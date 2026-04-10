import logging
from dataclasses import dataclass
from datetime import datetime
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from typing import Generator

from imapclient import IMAPClient

from config import EmailConfig

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    message_id: str
    subject: str
    received_at: datetime
    body_html: str
    body_text: str


class IMAPWatcher:
    def __init__(self, username: str, password: str, config: EmailConfig):
        self.username = username
        self.password = password
        self.config = config
        self._client: IMAPClient | None = None

    def _connect(self) -> IMAPClient:
        logger.info("Connecting to %s:%d", self.config.imap_host, self.config.imap_port)
        client = IMAPClient(self.config.imap_host, port=self.config.imap_port, ssl=True)
        client.login(self.username, self.password)
        client.select_folder(self.config.mailbox)
        return client

    def _ensure_connected(self) -> IMAPClient:
        if self._client is None:
            self._client = self._connect()
        else:
            try:
                self._client.noop()
            except Exception:
                logger.warning("IMAP connection lost, reconnecting")
                self._client = self._connect()
        return self._client

    def fetch_unread(self) -> Generator[tuple[int, EmailMessage], None, None]:
        client = self._ensure_connected()

        criteria = [
            "UNSEEN",
            "FROM", self.config.sender_filter,
            "SUBJECT", self.config.subject_filter,
        ]
        message_ids = client.search(criteria)

        if not message_ids:
            return

        logger.info("Found %d unread matching message(s)", len(message_ids))

        messages = client.fetch(message_ids, ["RFC822"])
        for uid, data in messages.items():
            raw = data[b"RFC822"]
            msg = message_from_bytes(raw)

            body_html = ""
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/html" and not body_html:
                        body_html = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                    elif content_type == "text/plain" and not body_text:
                        body_text = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
            else:
                payload = msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8", errors="replace"
                )
                if msg.get_content_type() == "text/html":
                    body_html = payload
                else:
                    body_text = payload

            date_str = msg.get("Date", "")
            try:
                received_at = parsedate_to_datetime(date_str)
            except Exception:
                received_at = datetime.now()

            yield uid, EmailMessage(
                message_id=msg.get("Message-ID", str(uid)),
                subject=msg.get("Subject", ""),
                received_at=received_at,
                body_html=body_html,
                body_text=body_text,
            )

    def mark_processed(self, uid: int) -> None:
        client = self._ensure_connected()
        label = self.config.processed_label
        try:
            client.copy([uid], label)
        except Exception:
            # Label may not support copy — fall back to just flagging
            logger.warning("Could not copy message to label '%s', skipping label", label)
        client.add_gmail_labels([uid], [label])
        client.add_flags([uid], [b"\\Seen"])
        logger.info("Marked message %s as processed", uid)

    def close(self) -> None:
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None
