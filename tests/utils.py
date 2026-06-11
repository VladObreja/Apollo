from datetime import datetime
from pathlib import Path
from apollo.domain.exceptions import ExtractionSchemaError, MarketDataError
from apollo.services.validate import OHLCVResult


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


class FakeEnvDataClient:
    """Returns canned environmental metrics for fingerprint tests."""

    def __init__(
        self,
        kp: float | None = 3.0,
        solar_wind: float | None = 450.0,
        raise_on_kp: bool = False,
        raise_on_wind: bool = False,
    ) -> None:
        self._kp = kp
        self._solar_wind = solar_wind
        self._raise_on_kp = raise_on_kp
        self._raise_on_wind = raise_on_wind

    def fetch_kp_index(self, timestamp: datetime) -> float | None:
        if self._raise_on_kp:
            raise OSError("Simulated Kp fetch failure")
        return self._kp

    def fetch_solar_wind_speed(self, timestamp: datetime) -> float | None:
        if self._raise_on_wind:
            raise OSError("Simulated solar wind fetch failure")
        return self._solar_wind


class FakeMarketDataClient:
    """Returns canned OHLCVResult per ticker for validation tests.

    If ticker not in responses, raises MarketDataError.
    Set raise_always=True to always raise (simulates outage).
    """

    def __init__(
        self,
        responses: dict[str, OHLCVResult] | None = None,
        raise_always: bool = False,
    ) -> None:
        self._responses: dict[str, OHLCVResult] = responses or {}
        self._raise_always = raise_always

    def fetch_ohlcv(self, ticker: str, expiry_at: datetime) -> OHLCVResult:
        if self._raise_always:
            raise MarketDataError("Simulated market data outage")
        if ticker not in self._responses:
            raise MarketDataError(f"No canned response for ticker {ticker!r}")
        return self._responses[ticker]


class FakeDiag:
    """Mimics psycopg2's `IntegrityError.orig.diag` for constraint-name checks."""

    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name


class FakeOrig(Exception):
    """Mimics psycopg2's `IntegrityError.orig`, carrying a `.diag.constraint_name`."""

    def __init__(self, constraint_name: str | None) -> None:
        super().__init__("duplicate key")
        self.diag = FakeDiag(constraint_name)
