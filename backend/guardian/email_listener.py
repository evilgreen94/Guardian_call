"""Real-Time Email Listener & IMAP Connector Module for Guardian 360 (Phase M1.5).

Connects securely via IMAP to Gmail, Outlook, or custom email providers,
fetches unseen incoming emails, extracts headers and body text, and passes
them through GuardianPipeline for real-time scam and phishing detection.
"""

import email
from email import policy
import imaplib
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Ensure .env is loaded
env_file = Path(__file__).resolve().parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from .events import EventSink, InMemoryEventSink
from .pipeline import GuardianPipeline, PipelineResult


@dataclass
class EmailMessageData:
    """Dataclass representing a parsed email message."""

    sender: str
    recipient: str
    subject: str
    date: str
    body_text: str
    raw_bytes: bytes


def parse_mime_email(raw_bytes: bytes) -> EmailMessageData:
    """Parse raw MIME bytes into a structured EmailMessageData dataclass."""
    try:
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    except Exception:
        msg = email.message_from_bytes(raw_bytes)

    sender = str(msg.get("From", ""))
    recipient = str(msg.get("To", ""))
    subject = str(msg.get("Subject", ""))
    date = str(msg.get("Date", ""))

    body_text = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text += payload.decode(part.get_content_charset() or "utf-8", errors="ignore") + "\n"
                except Exception:
                    pass
            elif content_type == "text/html" and not body_text and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_str = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                        # Basic HTML tag stripping
                        clean_text = re.sub(r"<[^>]+>", " ", html_str)
                        body_text += clean_text + "\n"
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
            else:
                body_text = str(msg.get_payload() or "")
        except Exception:
            body_text = str(msg.get_payload() or "")

    return EmailMessageData(
        sender=sender.strip(),
        recipient=recipient.strip(),
        subject=subject.strip(),
        date=date.strip(),
        body_text=body_text.strip(),
        raw_bytes=raw_bytes,
    )


class EmailListenerError(Exception):
    """Raised when IMAP connection, authentication, or fetching fails."""
    pass


class EmailListener:
    """IMAP client that connects to an email inbox and processes messages through GuardianPipeline."""

    def __init__(
        self,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        pipeline: Optional[GuardianPipeline] = None,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.imap_server = imap_server or os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.imap_port = imap_port or int(os.getenv("IMAP_PORT", "993"))
        self.username = username or os.getenv("IMAP_USER", "")
        self.password = password or os.getenv("IMAP_PASSWORD", "")
        self.pipeline = pipeline or GuardianPipeline()
        self.event_sink = event_sink

    def process_raw_email(self, raw_mime_bytes: bytes) -> PipelineResult:
        """Parse raw MIME email bytes and process through GuardianPipeline."""
        email_data = parse_mime_email(raw_mime_bytes)

        # Format complete email content string for analysis
        formatted_input = (
            f"EMAIL HEADER FROM: {email_data.sender}\n"
            f"EMAIL HEADER TO: {email_data.recipient}\n"
            f"EMAIL SUBJECT: {email_data.subject}\n\n"
            f"EMAIL BODY:\n{email_data.body_text}"
        )

        sink = self.event_sink or InMemoryEventSink()
        return self.pipeline.process_text(formatted_input, event_sink=sink)

    def fetch_and_process_unseen(self, mark_as_read: bool = False) -> List[Tuple[str, PipelineResult]]:
        """Connect to IMAP server, fetch all UNSEEN emails, and process them through Guardian Pipeline.

        Returns:
            List of tuples (msg_id, PipelineResult)
        """
        if not self.username or not self.password:
            raise EmailListenerError(
                "IMAP credentials missing! Please configure IMAP_USER and IMAP_PASSWORD in your .env file."
            )

        try:
            client = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            client.login(self.username, self.password)
            client.select("INBOX")

            # Search for unseen messages
            status_code, response = client.search(None, "UNSEEN")
            if status_code != "OK" or not response or not response[0]:
                client.logout()
                return []

            msg_ids = response[0].split()
            results: List[Tuple[str, PipelineResult]] = []

            for msg_id in msg_ids:
                fetch_flag = "(RFC822)" if mark_as_read else "(BODY.PEEK[])"
                res_code, data = client.fetch(msg_id, fetch_flag)
                if res_code == "OK" and data and isinstance(data[0], tuple):
                    raw_bytes = data[0][1]
                    result = self.process_raw_email(raw_bytes)
                    results.append((msg_id.decode("utf-8"), result))

            client.logout()
            return results

        except Exception as exc:
            raise EmailListenerError(f"Failed to fetch emails via IMAP: {str(exc)}") from exc


def main() -> None:
    """CLI runner to start polling IMAP inbox continuously."""
    import argparse

    parser = argparse.ArgumentParser(description="Guardian 360 — Real-Time IMAP Email Protection Listener")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval in seconds (default: 10s)")
    args = parser.parse_args()

    listener = EmailListener()
    print("=" * 70)
    print(f"GUARDIAN 360 — REAL-TIME EMAIL PROTECTION LISTENER")
    print(f"Server:   {listener.imap_server}:{listener.imap_port}")
    print(f"User:     {listener.username or '[NOT CONFIGURED - Set IMAP_USER in .env]'}")
    print(f"Interval: {args.interval}s")
    print("=" * 70)

    if not listener.username or not listener.password:
        print("\n[CONFIG NEEDED] To connect to your real email inbox:")
        print("1. Open your .env file")
        print("2. Set IMAP_USER=your_email@gmail.com")
        print("3. Set IMAP_PASSWORD=your_app_password  (Generate a 16-character App Password in Google Security)")
        print("4. Re-run: python backend/guardian/email_listener.py\n")
        return

    print("\nListening for incoming emails... Press CTRL+C to stop.\n")
    try:
        while True:
            try:
                results = listener.fetch_and_process_unseen(mark_as_read=False)
                if results:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processed {len(results)} new email(s):")
                    for msg_id, res in results:
                        print(f" -> Message ID #{msg_id} | Risk: {res.risk_assessment.level.value} | Action: {res.canary_decision.decision.value}")
                        if res.warning_event:
                            print(f"    [WARNING TRIGGERED] {res.warning_event.payload.get('headline')}: {res.risk_assessment.reasons}")
                else:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Polling INBOX... (No new unseen emails)")
            except EmailListenerError as err:
                print(f"[IMAP ERROR] {err}")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped Email Protection Listener.")


if __name__ == "__main__":
    main()
