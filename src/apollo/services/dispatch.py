"""Email dispatch service.

Implements the queued → dispatched lifecycle transition: renders the
Jinja2 tasking email, sends it via SMTP, and writes provenance columns
back to the corpus_record row.

The SMTPClient Protocol enables FakeSMTPClient injection in tests.
"""

from __future__ import annotations

import smtplib
from datetime import UTC, datetime
from email.mime.text import MIMEText
from typing import Protocol

from jinja2 import Environment
from sqlalchemy.orm import Session

from apollo.config import Settings
from apollo.db.models import CorpusRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.types import TargetStatus

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    AGENT_VERSION: str = _pkg_version("apollo")
except PackageNotFoundError:
    AGENT_VERSION = "0.0.0"


# ---------------------------------------------------------------------------
# SMTP Protocol & implementation
# ---------------------------------------------------------------------------


class SMTPClient(Protocol):
    """Protocol for sending a single email message."""

    def send_message(self, to: str, subject: str, body: str) -> None: ...


class SMTPClientImpl:
    """Concrete SMTP sender using Python stdlib smtplib only."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send_message(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._settings.smtp_from_address
        msg["To"] = to

        if self._settings.smtp_username and not self._settings.smtp_use_tls:
            raise ValueError("Refusing to send cleartext credentials over non-TLS SMTP")

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as server:
            if self._settings.smtp_use_tls:
                server.starttls()

            if self._settings.smtp_username:
                password = (
                    self._settings.smtp_password.get_secret_value()
                    if self._settings.smtp_password
                    else ""
                )
                server.login(self._settings.smtp_username, password)

            server.send_message(msg)


# ---------------------------------------------------------------------------
# DispatchService
# ---------------------------------------------------------------------------


class DispatchService:
    @staticmethod
    @requires(Compartment.TARGET_READ)
    def fetch_queued_for_dispatch(session: Session) -> list[CorpusRecord]:
        """Return all corpus_records in 'queued' status awaiting dispatch.

        Fetches without a lock — the dispatcher is the sole writer for the
        queued → dispatched transition. Each record is committed individually
        so SMTP failures don't block unrelated records.

        Args:
            session: Active SQLAlchemy session.

        Returns:
            List of queued CorpusRecord ORM objects (may be empty).
        """
        records: list[CorpusRecord] = (
            session.query(CorpusRecord)
            .filter(CorpusRecord.status == TargetStatus.QUEUED.value)
            .order_by(CorpusRecord.queued_at)
            .all()
        )
        return records

    @staticmethod
    def render_tasking_email(record: CorpusRecord, env: Environment) -> tuple[str, str]:
        """Render the Jinja2 tasking email for a queued record.

        Exposes ONLY the coordinate and parameter — never the target statement.
        This enforces double-blind anonymization at the template layer.

        Args:
            record: A queued CorpusRecord with a double_blind_coordinate set.
            env: A configured Jinja2 Environment with access to extraction.jinja.

        Returns:
            Tuple of (subject, body) strings.
        """
        if not record.double_blind_coordinate:
            raise ValueError(f"Record {record.id} missing double-blind coordinate")

        template = env.get_template("extraction.jinja")
        rendered = template.render(
            coordinate=record.double_blind_coordinate,
            parameter=record.parameter_name,
        )

        # The template's first line is "Subject: <subject text>"; split it off
        lines = rendered.splitlines()
        subject_line = lines[0] if lines else ""
        if not subject_line.startswith("Subject: "):
            raise ValueError("Template did not produce a valid 'Subject: ' header")

        subject = subject_line.removeprefix("Subject: ").strip()
        body = "\n".join(lines[1:]).lstrip("\n")

        if not body.strip():
            raise ValueError("Template rendered an empty email body")

        return subject, body

    @staticmethod
    @requires(Compartment.TARGET_WRITE)
    def mark_dispatched(
        record: CorpusRecord, session: Session, agent_version: str
    ) -> None:
        """Advance a corpus_record from 'queued' to 'dispatched' with provenance.

        Args:
            record: The CorpusRecord to advance (must be 'queued').
            session: Active SQLAlchemy session within a transaction.
            agent_version: The Apollo package version string to record.
        """
        if record.status != TargetStatus.QUEUED.value:
            raise ValueError(
                f"Cannot mark dispatched: record {record.id} is in status {record.status}"
            )
        record.status = TargetStatus.DISPATCHED.value
        record.dispatched_at = datetime.now(UTC)
        record.dispatch_agent_version = agent_version
        session.add(record)
