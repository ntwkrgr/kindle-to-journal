import logging
import time

from config import load_config
from journal.icloud_writer import write_entry
from processor.fetch import ExpiredLinkError, fetch_text, parse_entry
from watcher.imap_watcher import IMAPWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    watcher = IMAPWatcher(config.imap_username, config.imap_password, config.email)

    logger.info("Kindle Journal daemon started")

    try:
        while True:
            try:
                process_pending(watcher, config)
            except Exception as e:
                logger.error("Unexpected error in poll cycle: %s", e, exc_info=True)

            time.sleep(config.email.poll_interval_seconds)
    finally:
        watcher.close()


def process_pending(watcher: IMAPWatcher, config) -> None:
    for uid, email in watcher.fetch_unread():
        logger.info("Processing message %s: %s", uid, email.subject)

        # Step 1: Fetch and parse the text file
        try:
            raw_text = fetch_text(email, config.fetch)
            entry = parse_entry(raw_text)
        except ExpiredLinkError as e:
            logger.error("Expired link for message %s: %s — marking as read", uid, e)
            watcher.mark_processed(uid)
            continue
        except Exception as e:
            logger.error("Failed to fetch/parse message %s: %s — will retry next poll", uid, e)
            continue

        # Step 2: Write entry to iCloud Drive
        try:
            write_entry(entry.title, entry.body, config.journal)
        except Exception as e:
            logger.error("Failed to write entry for message %s: %s — will retry next poll", uid, e)
            continue

        # Step 3: Mark email as processed
        try:
            watcher.mark_processed(uid)
        except Exception as e:
            logger.error("Failed to mark message %s as processed: %s", uid, e)


if __name__ == "__main__":
    main()
