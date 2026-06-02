"""Inbound email polling service.

Polls an IMAP mailbox for unseen Asset reply emails, matches each to a
dispatched corpus_record by double-blind coordinate, and durably stores the
raw MIME bytes before handing off to ExtractionService.

Idempotency guarantee: IMAP messages are marked SEEN unconditionally after
fetch — even if no matching corpus_record is found — so failed or unmatched
emails are not re-processed on subsequent ticks.

Raw bytes are committed in their own DB transaction before the LLM extraction
call (in worker.py). If the process is killed after storage but before
extraction, the raw bytes survive and Story 2.3 can recover them.
"""

from __future__ import annotations

import imaplib
import re
from datetime import UTC, datetime
from email.parser import BytesParser
from email.policy import default as email_default_policy
from typing import Protocol

from sqlalchemy.orm import Session

from apollo.config import Settings
from apollo.db.models import CorpusRecord
from apollo.db.session import get_session_factory
from apollo.domain.compartments import Compartment, requires
from apollo.domain.types import TargetStatus

_COORD_RE = re.compile(r"Target ID ([A-Z0-9]{4}/[A-Z0-9]{4})")


# ---------------------------------------------------------------------------
# IMAPClient Protocol & implementation
# ---------------------------------------------------------------------------


class IMAPClient(Protocol):
    """Protocol for fetching unseen IMAP messages."""

    def fetch_unseen_emails(self) -> list[bytes]: ...


class IMAPClientImpl:
    """Concrete IMAP client using Python stdlib imaplib.

    Marks each fetched message as SEEN unconditionally so retries on
    the next tick don't reprocess the same message.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_unseen_emails(self) -> list[bytes]:
        imap_class: type[imaplib.IMAP4] = (
            imaplib.IMAP4_SSL if self._settings.imap_use_ssl else imaplib.IMAP4
        )
        try:
            with imap_class(self._settings.imap_host, self._settings.imap_port) as conn:
                conn.login(
                    self._settings.imap_username,
                    self._settings.imap_password.get_secret_value(),
                )
                status, _ = conn.select(self._settings.imap_mailbox)
                if status != "OK":
                    return []
                status, uid_data = conn.search(None, "UNSEEN")
                if status != "OK" or not uid_data or not uid_data[0]:
                    return []
                raw_emails: list[bytes] = []
                for uid in uid_data[0].split():
                    try:
                        _, msg_data = conn.fetch(uid, "(RFC822)")
                        if msg_data and msg_data[0]:
                            raw_bytes = msg_data[0][1]
                            if isinstance(raw_bytes, bytes):
                                raw_emails.append(raw_bytes)
                                # Mark SEEN only if we got valid bytes
                                conn.store(uid, "+FLAGS", r"\Seen")
                    except imaplib.IMAP4.error:
                        continue
                return raw_emails
        except (imaplib.IMAP4.error, OSError):
            return []


# ---------------------------------------------------------------------------
# EmailPollerService
# ---------------------------------------------------------------------------


class EmailPollerService:
    @staticmethod
    def parse_coordinate_from_subject(subject: str) -> str | None:
        """Extract a double-blind coordinate from an email subject line.

        Matches pattern: 'Target ID XXXX/YYYY' where X/Y are uppercase
        alphanumeric characters (4+4 format).

        Returns None if subject does not match.
        """
        m = _COORD_RE.search(subject)
        return m.group(1) if m else None

    @staticmethod
    def parse_email_body(raw_bytes: bytes) -> str:
        """Extract the plain-text body from raw MIME bytes.

        For multipart messages, returns the first text/plain part.
        Falls back to the root payload for non-multipart messages.
        Returns empty string if no text content is found.
        """
        msg = BytesParser(policy=email_default_policy).parsebytes(raw_bytes)
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="replace")
            # Fallback for multipart with no text/plain
            return ""
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode("utf-8", errors="replace")
        return ""

    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def store_raw_email(
        record: CorpusRecord, raw_bytes: bytes, session: Session
    ) -> None:
        """Persist raw MIME bytes and reception timestamp onto a corpus_record.

        Called inside a write transaction in fetch_new_session_emails. Raw bytes
        are the only strictly immutable artifact — they must be stored before
        any LLM extraction so they survive process crashes.
        """
        record.raw_email_bytes = raw_bytes
        record.received_at = datetime.now(UTC)
        session.add(record)

    @staticmethod
    def fetch_new_session_emails(
        session: Session, session_factory: Any, imap_client: IMAPClient
    ) -> list[tuple[CorpusRecord, bytes]]:
        """Poll IMAP, match emails to dispatched records, store raw bytes.

        For each unseen email:
          1. Parse subject to extract coordinate.
          2. Look up a dispatched corpus_record with that coordinate.
          3. If found: store raw_email_bytes + received_at in a write transaction.
          4. Return matched (record, raw_bytes) pairs for extraction.

        Emails with unrecognised coordinates are silently skipped (logged
        externally by the caller).

        Args:
            session: Read session for coordinate lookup queries.
            session_factory: Factory for write transactions.
            imap_client: IMAPClient implementation.

        Returns:
            List of (CorpusRecord, raw_bytes) pairs ready for extraction.
        """
        raw_emails = imap_client.fetch_unseen_emails()
        matched: list[tuple[CorpusRecord, bytes]] = []

        for raw_bytes in raw_emails:
            msg = BytesParser(policy=email_default_policy).parsebytes(raw_bytes)
            subject = str(msg.get("subject") or "")
            coord = EmailPollerService.parse_coordinate_from_subject(subject)
            if coord is None:
                continue

            record: CorpusRecord | None = (
                session.query(CorpusRecord)
                .filter(
                    CorpusRecord.double_blind_coordinate == coord,
                    CorpusRecord.status == TargetStatus.DISPATCHED.value,
                )
                .first()
            )
            if record is None:
                continue

            # Commit raw bytes in a dedicated write transaction before extraction
            try:
                with session_factory.begin() as write_session:
                    fresh: CorpusRecord | None = write_session.get(CorpusRecord, record.id)
                    if fresh is None or fresh.status != TargetStatus.DISPATCHED.value:
                        continue
                    if fresh.raw_email_bytes is not None:
                        continue
                    EmailPollerService.store_raw_email(fresh, raw_bytes, write_session)
                
                # Update the read session record so downstream has the bytes
                session.refresh(record)
                matched.append((record, raw_bytes))
            except Exception:
                continue

        return matched
