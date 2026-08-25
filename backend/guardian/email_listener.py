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
import sys
from pathlib import Path
from typing import List, Optional, Tuple

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Ensure .env is loaded
env_file = backend_dir.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

try:
    from .events import InMemoryEventSink
    from .pipeline import GuardianPipeline, PipelineResult
except ImportError:
    from guardian.events import InMemoryEventSink
    from guardian.pipeline import GuardianPipeline, PipelineResult


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
        event_sink: Optional[InMemoryEventSink] = None,
    ) -> None:
        self.imap_server = imap_server or os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.imap_port = imap_port or int(os.getenv("IMAP_PORT", "993"))
        self.username = username or os.getenv("IMAP_USER", "")
        self.password = password or os.getenv("IMAP_PASSWORD", "")
        self.pipeline = pipeline or GuardianPipeline()
        self.event_sink = event_sink
        self.processed_msg_ids = set()

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
        res = self.pipeline.process_text(formatted_input, event_sink=sink)
        self._publish_to_server(email_data.sender, email_data.subject, res)
        return res

    def _publish_to_server(self, sender: str, subject: str, result: PipelineResult) -> None:
        """Publish analyzed email result to backend FastAPI server for real-time visualizer streaming."""
        if os.getenv("PYTEST_CURRENT_TEST"):
            return

        import json
        import urllib.request

        payload = {
            "event_type": "REALTIME_EMAIL_ANALYSIS",
            "source": "IMAP_LISTENER",
            "sender": sender,
            "subject": subject,
            "risk_level": result.risk_assessment.level.value,
            "decision": result.canary_decision.decision.value,
            "reasons": result.risk_assessment.reasons,
            "headline": result.warning_event.payload.get("headline") if result.warning_event else None,
            "signals": result.signals.to_dict(),
            "events": [e.to_dict() for e in result.events],
        }
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8080/api/v1/events/publish",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=0.1):
                pass
        except Exception:
            pass

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
                msg_id_str = msg_id.decode("utf-8")
                if msg_id_str in self.processed_msg_ids:
                    continue

                fetch_flag = "(RFC822)" if mark_as_read else "(BODY.PEEK[])"
                res_code, data = client.fetch(msg_id, fetch_flag)
                if res_code == "OK" and data and isinstance(data[0], tuple):
                    raw_bytes = data[0][1]
                    result = self.process_raw_email(raw_bytes)
                    self.processed_msg_ids.add(msg_id_str)
                    results.append((msg_id_str, result))

            client.logout()
            return results

        except Exception as exc:
            raise EmailListenerError(f"Failed to fetch emails via IMAP: {str(exc)}") from exc

    def scan_recent_emails(self, limit: int = 5) -> List[Tuple[str, PipelineResult]]:
        """Connect to IMAP server, fetch recent N emails in INBOX, and process them through Guardian Pipeline.

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

            # Search for all messages and take the last 'limit'
            status_code, response = client.search(None, "ALL")
            if status_code != "OK" or not response or not response[0]:
                client.logout()
                return []

            msg_ids = response[0].split()
            recent_ids = msg_ids[-limit:] if len(msg_ids) >= limit else msg_ids
            results: List[Tuple[str, PipelineResult]] = []

            for msg_id in recent_ids:
                res_code, data = client.fetch(msg_id, "(BODY.PEEK[])")
                if res_code == "OK" and data and isinstance(data[0], tuple):
                    raw_bytes = data[0][1]
                    result = self.process_raw_email(raw_bytes)
                    results.append((msg_id.decode("utf-8"), result))

            client.logout()
            return results

        except Exception as exc:
            raise EmailListenerError(f"Failed to scan recent emails via IMAP: {str(exc)}") from exc


def main() -> None:
    """CLI runner to start polling IMAP inbox continuously."""
    import argparse

    parser = argparse.ArgumentParser(description="Guardian 360 — Real-Time IMAP Email Protection Listener")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval in seconds (default: 10s)")
    args = parser.parse_args()

    listener = EmailListener()
    print("=" * 70, flush=True)
    print(f"GUARDIAN 360 — REAL-TIME EMAIL PROTECTION LISTENER", flush=True)
    print(f"Server:   {listener.imap_server}:{listener.imap_port}", flush=True)
    print(f"User:     {listener.username or '[NOT CONFIGURED - Set IMAP_USER in .env]'}", flush=True)
    print(f"Interval: {args.interval}s", flush=True)
    print("=" * 70, flush=True)

    if not listener.username or not listener.password:
        print("\n[CONFIG NEEDED] To connect to your real email inbox:", flush=True)
        print("1. Open your .env file", flush=True)
        print("2. Set IMAP_USER=your_email@gmail.com", flush=True)
        print("3. Set IMAP_PASSWORD=your_app_password  (Generate a 16-character App Password in Google Security)", flush=True)
        print("4. Re-run: python backend/guardian/email_listener.py\n", flush=True)
        return

    print("\nListening for incoming emails... Press CTRL+C to stop.\n", flush=True)
    try:
        while True:
            try:
                results = listener.fetch_and_process_unseen(mark_as_read=False)
                if results:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processed {len(results)} new email(s):", flush=True)
                    for msg_id, res in results:
                        print(f" -> Message ID #{msg_id} | Risk: {res.risk_assessment.level.value} | Action: {res.canary_decision.decision.value}", flush=True)
                        if res.warning_event:
                            print(f"    [WARNING TRIGGERED] {res.warning_event.payload.get('headline')}: {res.risk_assessment.reasons}", flush=True)
                else:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Polling INBOX... (No new unseen emails)", flush=True)
            except EmailListenerError as err:
                print(f"[IMAP ERROR] {err}", flush=True)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped Email Protection Listener.")


if __name__ == "__main__":
    main()
