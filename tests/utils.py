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
