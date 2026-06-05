"""Unit tests for ExtractionService — no DB, no Ollama, no network."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from jinja2 import Environment, FileSystemLoader

from apollo.domain.exceptions import ExtractionSchemaError
from apollo.domain.models import ExtractionResultSchema
from apollo.services.extract import ExtractionService
from tests.utils import FakeLLM, get_templates_dir


def _make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(get_templates_dir())), autoescape=False
    )


def _make_record(coordinate: str = "8A2F/9B4C", parameter: str = "vad") -> MagicMock:
    record = MagicMock()
    record.double_blind_coordinate = coordinate
    record.parameter_name = parameter
    return record


def _valid_json(param_value: float = 75.0) -> str:
    return json.dumps({"param_value": param_value})


class TestExtractionServiceSuccess:
    def test_extract_success(self) -> None:
        """FakeLLM returns valid JSON → ExtractionResultSchema returned."""
        env = _make_env()
        record = _make_record()
        llm = FakeLLM([_valid_json(72.0)])

        result = ExtractionService.extract(record, "PARAM (vad): 72", llm, env)

        assert isinstance(result, ExtractionResultSchema)
        assert result.param_value == 72.0

    def test_extract_success_with_all_fields(self) -> None:
        """Full JSON with all optional fields validated correctly."""
        env = _make_env()
        record = _make_record()
        full_json = json.dumps(
            {
                "param_value": 80.0,
                "measurement_timestamp": "2026-06-02T14:30:00Z",
                "asset_location": "Bucharest",
                "sleep_quality": 90.0,
                "psychological_state": 75.0,
                "social_field": "Isolated",
                "asset_notes": "Clear signal.",
            }
        )
        llm = FakeLLM([full_json])

        result = ExtractionService.extract(record, "email body", llm, env)

        assert result.param_value == 80.0
        assert result.asset_location == "Bucharest"
        assert result.social_field == "Isolated"
        assert result.asset_notes == "Clear signal."

    def test_extract_calls_llm_once_on_success(self) -> None:
        """LLM is called exactly once when first response is valid."""
        env = _make_env()
        record = _make_record()
        llm = FakeLLM([_valid_json(50.0)])

        ExtractionService.extract(record, "body", llm, env)

        assert llm._call_count == 1


class TestExtractionServiceRetry:
    def test_extract_retries_on_validation_error(self) -> None:
        """On first invalid JSON, ExtractionService retries once."""
        env = _make_env()
        record = _make_record()
        llm = FakeLLM(["not valid json", _valid_json(60.0)])

        result = ExtractionService.extract(record, "body", llm, env)

        assert llm._call_count == 2
        assert result.param_value == 60.0

    def test_retry_prompt_contains_error_text(self) -> None:
        """Retry prompt must include the validation error from the first attempt."""
        env = _make_env()
        record = _make_record()
        llm = MagicMock()
        llm.extract.side_effect = ["not valid json", _valid_json(50.0)]

        ExtractionService.extract(record, "body", llm, env)

        assert llm.extract.call_count == 2
        retry_prompt = llm.extract.call_args_list[1][0][0]
        assert (
            "Error on previous attempt:" in retry_prompt
            or "error" in retry_prompt.lower()
        )

    def test_extract_retries_on_schema_validation_error(self) -> None:
        """param_value out-of-range triggers retry."""
        env = _make_env()
        record = _make_record()
        invalid = json.dumps({"param_value": 200.0})
        valid = _valid_json(55.0)
        llm = FakeLLM([invalid, valid])

        result = ExtractionService.extract(record, "body", llm, env)

        assert llm._call_count == 2
        assert result.param_value == 55.0


class TestExtractionServiceFailure:
    def test_extract_raises_extraction_schema_error_after_two_failures(self) -> None:
        """Two consecutive invalid responses → ExtractionSchemaError raised."""
        env = _make_env()
        record = _make_record()
        llm = FakeLLM(["invalid", "also invalid"])

        with pytest.raises(ExtractionSchemaError):
            ExtractionService.extract(record, "body", llm, env)

    def test_raises_extraction_schema_error_not_value_error(self) -> None:
        """Must raise ExtractionSchemaError, never bare ValueError."""
        env = _make_env()
        record = _make_record()
        llm = FakeLLM(["{}", "{}"])

        with pytest.raises(ExtractionSchemaError):
            ExtractionService.extract(record, "body", llm, env)

    def test_llm_called_exactly_twice_on_double_failure(self) -> None:
        """LLM is called exactly twice (original + 1 retry) — no extra calls."""
        env = _make_env()
        record = _make_record()
        llm = FakeLLM(["bad1", "bad2"])

        with pytest.raises(ExtractionSchemaError):
            ExtractionService.extract(record, "body", llm, env)

        assert llm._call_count == 2
