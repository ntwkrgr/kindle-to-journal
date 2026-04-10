import logging
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from config import FetchConfig
from watcher.imap_watcher import EmailMessage

logger = logging.getLogger(__name__)


class ExpiredLinkError(Exception):
    pass


@dataclass
class ParsedEntry:
    title: str
    body: str


def fetch_text(email: EmailMessage, config: FetchConfig) -> str:
    url = _find_download_url(email.body_html, config.preferred_format)
    logger.info("Fetching download URL for message '%s'", email.subject)

    response = requests.get(
        url,
        headers={"User-Agent": config.user_agent},
        timeout=config.request_timeout_seconds,
        allow_redirects=True,
    )

    if response.status_code == 403 or response.status_code == 410:
        raise ExpiredLinkError(
            f"Download link returned {response.status_code} — link has likely expired"
        )

    response.raise_for_status()

    text = response.text.strip()
    if not text:
        raise ValueError("Downloaded file is empty")

    return text


def parse_entry(raw_text: str) -> ParsedEntry:
    lines = raw_text.splitlines()

    # Remove leading blank lines
    while lines and not lines[0].strip():
        lines.pop(0)

    if len(lines) < 2:
        raise ValueError(
            f"Text file has fewer than 2 lines after stripping blanks; cannot extract title"
        )

    # Line 1: page number — discard
    # Line 2: title (strip leading '# ' and whitespace)
    title = lines[1].lstrip("#").strip()

    if not title:
        raise ValueError("Title line (line 2) is empty after stripping")

    # Lines 3+: body
    body = "\n".join(lines[2:]).strip()

    return ParsedEntry(title=title, body=body)


def _find_download_url(body_html: str, preferred_format: str) -> str:
    soup = BeautifulSoup(body_html, "html.parser")

    format_labels = {
        "text": ["download text file", "download the text file"],
        "pdf": ["download searchable pdf", "download the searchable pdf", "download pdf"],
    }

    preferred_labels = format_labels.get(preferred_format, format_labels["text"])
    fallback_labels = [label for key, labels in format_labels.items() for label in labels]

    for labels in (preferred_labels, fallback_labels):
        for anchor in soup.find_all("a", href=True):
            if anchor.get_text(strip=True).lower() in labels:
                return anchor["href"]

    raise ValueError(
        "Could not find a download link in the email body. "
        "The email format may have changed."
    )
