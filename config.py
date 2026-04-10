import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class EmailConfig:
    imap_host: str
    imap_port: int
    poll_interval_seconds: int
    sender_filter: str
    subject_filter: str
    mailbox: str
    processed_label: str


@dataclass
class FetchConfig:
    preferred_format: str
    request_timeout_seconds: int
    user_agent: str


@dataclass
class JournalConfig:
    pending_folder: Path
    dry_run: bool


@dataclass
class Config:
    imap_username: str
    imap_password: str
    email: EmailConfig
    fetch: FetchConfig
    journal: JournalConfig


def load_config(config_path: str = "config.yaml") -> Config:
    load_dotenv()

    imap_username = os.environ.get("IMAP_USERNAME")
    imap_password = os.environ.get("IMAP_PASSWORD")

    if not imap_username:
        raise RuntimeError("IMAP_USERNAME environment variable is required")
    if not imap_password:
        raise RuntimeError("IMAP_PASSWORD environment variable is required")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    email_raw = raw["email"]
    fetch_raw = raw["fetch"]
    journal_raw = raw["journal"]

    return Config(
        imap_username=imap_username,
        imap_password=imap_password,
        email=EmailConfig(
            imap_host=email_raw["imap_host"],
            imap_port=email_raw["imap_port"],
            poll_interval_seconds=email_raw["poll_interval_seconds"],
            sender_filter=email_raw["sender_filter"],
            subject_filter=email_raw["subject_filter"],
            mailbox=email_raw["mailbox"],
            processed_label=email_raw["processed_label"],
        ),
        fetch=FetchConfig(
            preferred_format=fetch_raw["preferred_format"],
            request_timeout_seconds=fetch_raw["request_timeout_seconds"],
            user_agent=fetch_raw["user_agent"],
        ),
        journal=JournalConfig(
            pending_folder=Path(journal_raw["pending_folder"]).expanduser(),
            dry_run=journal_raw.get("dry_run", False),
        ),
    )
