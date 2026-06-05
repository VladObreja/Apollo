from pathlib import Path
from apollo.domain.exceptions import ExtractionSchemaError


def get_templates_dir() -> Path:
    return Path(__file__).parent.parent / "src" / "apollo" / "templates"


class FakeSMTPClient:
    """Captures sent emails; optionally raises OSError on the nth call."""

    def __init__(self, raise_on_nth: int | None = None) -> None:
        self.sent: list[dict[str, str]] = []
        self._raise_on_nth = raise_on_nth
        self._call_count = 0

    def send_message(self, to: str, subject: str, body: str) -> None:
        self._call_count += 1
        if self._raise_on_nth is not None and self._call_count == self._raise_on_nth:
            raise OSError("Simulated SMTP failure")
        self.sent.append({"to": to, "subject": subject, "body": body})


class FakeLLM:
    """Returns canned JSON strings for LLM extraction tests.

    Responses are consumed in order. AssertionError on extra calls.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._call_count = 0

    def extract(self, prompt: str, schema: object) -> str:
        if self._call_count >= len(self._responses):
            raise ExtractionSchemaError(
                f"FakeLLM called {self._call_count + 1} times but only "
                f"{len(self._responses)} response(s) configured"
            )
        response = self._responses[self._call_count]
        self._call_count += 1
        return response


class FakeIMAPClient:
    """Returns canned raw MIME bytes as unseen emails."""

    def __init__(self, raw_emails: list[bytes]) -> None:
        self._raw_emails = raw_emails

    def fetch_unseen_emails(self) -> list[bytes]:
        return list(self._raw_emails)
