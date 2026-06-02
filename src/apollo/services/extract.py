"""LLM extraction service.

Implements schema-constrained extraction of Asset reply emails via a local
Ollama LLM. The LLMClient Protocol enables FakeLLM injection in tests —
the real Ollama instance is never called during the test suite.

Extraction flow (one bounded retry on ValidationError):
    1. Render Jinja2 extraction_prompt.jinja with record context + email body.
    2. Call llm_client.extract(prompt, json_schema) → raw JSON string.
    3. Parse + validate with ExtractionResultSchema.model_validate().
    4. On ValidationError/JSONDecodeError: append error to prompt, retry once.
    5. On second failure: raise ExtractionSchemaError (never a bare ValueError).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from jinja2 import Environment
from pydantic import ValidationError
from sqlalchemy.orm import Session

from apollo.db.models import CorpusRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.exceptions import ExtractionSchemaError
from apollo.domain.models import ExtractionResultSchema


# ---------------------------------------------------------------------------
# LLMClient Protocol & Ollama implementation
# ---------------------------------------------------------------------------


class LLMClient(Protocol):
    """Protocol for schema-constrained LLM extraction calls."""

    def extract(self, prompt: str, schema: dict[str, Any]) -> str: ...


class OllamaClientImpl:
    """Concrete Ollama client using stdlib urllib.request only.

    Passes the JSON schema as the `format` field in the Ollama /api/generate
    request body, enabling structured output constrained by the Pydantic schema.
    """

    def __init__(self, base_url: str, model_digest: str, timeout: int = 60) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_digest = model_digest
        self._timeout = timeout

    def extract(self, prompt: str, schema: dict[str, Any]) -> str:
        payload = json.dumps(
            {
                "model": self._model_digest,
                "prompt": prompt,
                "format": schema,
                "stream": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result: dict[str, Any] = json.loads(resp.read())
            if "response" not in result:
                raise ExtractionSchemaError("Ollama response missing 'response' key")
            return str(result["response"])
        except urllib.error.URLError as e:
            raise ExtractionSchemaError(f"Network error calling Ollama: {e}") from e
        except json.JSONDecodeError as e:
            raise ExtractionSchemaError(f"Invalid JSON from Ollama API: {e}") from e


# ---------------------------------------------------------------------------
# ExtractionService
# ---------------------------------------------------------------------------


class ExtractionService:
    @staticmethod
    def render_extraction_prompt(record: CorpusRecord, email_body: str, env: Environment) -> str:
        try:
            template = env.get_template("extraction_prompt.jinja")
            return template.render(
                coordinate=record.double_blind_coordinate,
                parameter=record.parameter_name,
                email_body=email_body,
            )
        except Exception as e:
            raise ExtractionSchemaError(f"Template rendering failed: {e}") from e

    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def extract(
        record: CorpusRecord,
        email_body: str,
        llm_client: LLMClient,
        env: Environment,
    ) -> ExtractionResultSchema:
        """Extract measurements from email body via LLM with one bounded retry.

        Args:
            record: The corpus_record whose email is being extracted.
            email_body: Plain-text body of the Asset reply email.
            llm_client: LLMClient implementation (OllamaClientImpl or FakeLLM).
            env: Jinja2 Environment with access to extraction_prompt.jinja.

        Returns:
            Validated ExtractionResultSchema.

        Raises:
            ExtractionSchemaError: If LLM fails to produce valid output after retry.
        """
        schema = ExtractionResultSchema.model_json_schema()
        prompt = ExtractionService.render_extraction_prompt(record, email_body, env)

        try:
            raw = llm_client.extract(prompt, schema)
            return ExtractionResultSchema.model_validate(json.loads(raw))
        except (ValidationError, json.JSONDecodeError, ExtractionSchemaError) as first_err:
            retry_prompt = (
                f"{prompt}\n\nError on previous attempt: {first_err}\n"
                "Please correct your response and return valid JSON."
            )
            try:
                raw_retry = llm_client.extract(retry_prompt, schema)
                return ExtractionResultSchema.model_validate(json.loads(raw_retry))
            except (ValidationError, json.JSONDecodeError, ExtractionSchemaError) as final_err:
                raise ExtractionSchemaError(
                    f"LLM failed to produce valid ExtractionResultSchema after 1 retry: {final_err}"
                ) from final_err
