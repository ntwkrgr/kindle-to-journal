import json
import logging
from datetime import datetime
from pathlib import Path

from config import JournalConfig

logger = logging.getLogger(__name__)


def write_entry(title: str, body: str, config: JournalConfig) -> None:
    if config.dry_run:
        print(f"[dry_run] Title: {title}")
        print(f"[dry_run] Body:\n{body}")
        return

    folder = config.pending_folder
    folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = folder / f"{timestamp}-entry.json"

    payload = {"title": title, "body": body}
    filename.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    logger.info("Wrote entry '%s' to %s", title, filename)
