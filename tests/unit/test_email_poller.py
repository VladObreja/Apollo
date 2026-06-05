"""Unit tests for EmailPollerService — no DB IO, no IMAP, no network."""

from __future__ import annotations

import email.mime.multipart
import email.mime.text
from email.mime.text import MIMEText
from unittest.mock import MagicMock


from apollo.services.email_poller import EmailPollerService
from tests.utils import FakeIMAPClient


def _make_raw_email(subject: str, body: str, html_body: str | None = None) -> bytes:
    """Build raw MIME bytes for a plain-text (or multipart) email."""
    if html_body is not None:
        msg: email.mime.multipart.MIMEMultipart | MIMEText = (
            email.mime.multipart.MIMEMultipart("alternative")
        )
        msg["Subject"] = subject
        msg["From"] = "asset@proton.me"
        msg["To"] = "apollo@proton.me"
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    else:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = "asset@proton.me"
        msg["To"] = "apollo@proton.me"
    return msg.as_bytes()


class TestParseCoordinateFromSubject:
    def test_parse_coordinate_from_subject_valid(self) -> None:
        coord = EmailPollerService.parse_coordinate_from_subject(
            "Re: Apollo Research Session — Target ID 8A2F/9B4C"
        )
        assert coord == "8A2F/9B4C"

    def test_parse_coordinate_from_subject_no_match(self) -> None:
        coord = EmailPollerService.parse_coordinate_from_subject("Hello World")
        assert coord is None

    def test_empty_subject_returns_none(self) -> None:
        assert EmailPollerService.parse_coordinate_from_subject("") is None

    def test_coordinate_at_start_of_subject(self) -> None:
        coord = EmailPollerService.parse_coordinate_from_subject(
            "Target ID ZZZZ/9999 something"
        )
        assert coord == "ZZZZ/9999"

    def test_lowercase_coordinate_not_matched(self) -> None:
        coord = EmailPollerService.parse_coordinate_from_subject("Target ID abcd/1234")
        assert coord is None


class TestParseEmailBody:
    def test_parse_email_body_plain_text(self) -> None:
        raw = _make_raw_email("Subject", "Hello body text")
        body = EmailPollerService.parse_email_body(raw)
        assert "Hello body text" in body

    def test_parse_email_body_multipart(self) -> None:
        raw = _make_raw_email(
            "Subject",
            "Plain text part",
            html_body="<p>HTML part</p>",
        )
        body = EmailPollerService.parse_email_body(raw)
        assert "Plain text part" in body
        assert "<p>" not in body

    def test_empty_bytes_returns_empty_string(self) -> None:
        # Minimal valid MIME with no payload
        msg = MIMEText("", "plain", "utf-8")
        body = EmailPollerService.parse_email_body(msg.as_bytes())
        assert body == ""


class TestFetchNewSessionEmails:
    def _make_dispatched_record(self, coord: str) -> MagicMock:
        record = MagicMock()
        record.id = "test-uuid-1234"
        record.double_blind_coordinate = coord
        record.status = "dispatched"
        record.raw_email_bytes = None
        return record

    def test_fetch_new_session_emails_matches_dispatched_record(self) -> None:
        """Email with matching coordinate → 1 pair returned, raw bytes stored."""
        coord = "8A2F/9B4C"
        raw = _make_raw_email(
            f"Re: Apollo Research Session — Target ID {coord}",
            "PARAM (vad): 75",
        )
        imap_client = FakeIMAPClient([raw])
        record = self._make_dispatched_record(coord)

        # Fake session that returns our record on query
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = record

        mock_write_session = MagicMock()
        mock_write_session.__enter__ = MagicMock(return_value=mock_write_session)
        mock_write_session.__exit__ = MagicMock(return_value=False)
        mock_sf = MagicMock()
        mock_sf.begin.return_value = mock_write_session
        mock_write_session.get.return_value = record

        result = EmailPollerService.fetch_new_session_emails(
            mock_session, mock_sf, imap_client
        )

        assert len(result) == 1
        assert result[0][0] is record
        assert result[0][1] == raw

    def test_fetch_new_session_emails_ignores_unknown_coordinate(self) -> None:
        """Email with unknown coordinate → empty list returned."""
        raw = _make_raw_email(
            "Re: Apollo Research Session — Target ID XXXX/YYYY",
            "PARAM (vad): 75",
        )
        imap_client = FakeIMAPClient([raw])

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No matching record

        mock_sf = MagicMock()
        result = EmailPollerService.fetch_new_session_emails(
            mock_session, mock_sf, imap_client
        )

        assert result == []

    def test_ignores_email_without_coordinate_in_subject(self) -> None:
        """Email with no coordinate in subject → empty list, no DB query."""
        raw = _make_raw_email("Random subject line", "Some body")
        imap_client = FakeIMAPClient([raw])

        mock_session = MagicMock()
        mock_sf = MagicMock()

        result = EmailPollerService.fetch_new_session_emails(
            mock_session, mock_sf, imap_client
        )

        assert result == []
        mock_session.query.assert_not_called()

    def test_stores_raw_email_bytes_on_record(self) -> None:
        """store_raw_email sets raw_email_bytes and received_at on the record."""
        from datetime import datetime

        record = MagicMock()
        session = MagicMock()
        raw = b"raw mime bytes"

        EmailPollerService.store_raw_email(record, raw, session)

        assert record.raw_email_bytes == raw
        assert record.received_at is not None
        # received_at must be timezone-aware UTC
        # We can't assert exact time, but must be a datetime
        assert isinstance(record.received_at, datetime)
        session.add.assert_called_once_with(record)
