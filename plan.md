# Kindle Scribe → Apple Journal Automation

## Overview

A Python daemon running on Mac Mini that watches a Gmail inbox for Kindle Scribe notebook exports, downloads the converted text file from Amazon's download link, and writes a JSON entry file to iCloud Drive. An iOS Shortcut automation picks up the file and creates an Apple Journal entry.

No OCR or Vision API required — the Kindle "Convert to text and send" option produces a plain text file directly.

## Architecture

```
Kindle Scribe (manual "Convert to text and send")
    → Gmail inbox (email with expiring download links)
    → Mac Mini daemon (launchd)
    → HTTP fetch (Amazon download link → .txt file)
    → JSON entry file written to iCloud Drive folder
    → [iCloud sync]
    → iOS Shortcut automation (triggered by new file in folder)
    → Apple Journal.app → iCloud sync → iPhone/iPad
```

## Repository Layout

```
kindle-journal/
├── main.py                 # Entry point, starts the watcher loop
├── config.py               # Config loader (env vars + config.yaml)
├── watcher/
│   ├── __init__.py
│   └── imap_watcher.py     # Gmail IMAP polling
├── processor/
│   ├── __init__.py
│   └── fetch.py            # Parse email body for download link, fetch and parse text file
├── journal/
│   ├── __init__.py
│   └── icloud_writer.py    # Write entry JSON file to iCloud Drive pending folder
├── config.yaml.example
├── com.chasrogers.kindle-journal.plist   # launchd service definition
├── requirements.txt
├── plan.md
└── README.md
```

## Configuration

Secrets via environment variables (`.env`, loaded by `python-dotenv`). Non-secret config in `config.yaml`.

### Environment Variables

| Variable | Purpose |
|---|---|
| `IMAP_USERNAME` | Gmail address |
| `IMAP_PASSWORD` | Gmail App Password (not account password — requires 2FA + App Password in Google account settings) |

### config.yaml

```yaml
email:
  imap_host: "imap.gmail.com"
  imap_port: 993
  poll_interval_seconds: 60
  sender_filter: "do-not-reply@amazon.com"
  subject_filter: "You sent a file"               # Confirmed from email subject pattern
  mailbox: "INBOX"
  processed_label: "kindle-processed"             # Gmail label to apply after processing

fetch:
  preferred_format: "text"        # "text" or "pdf" — text is sufficient, no reason to use PDF
  request_timeout_seconds: 30
  user_agent: "Mozilla/5.0"       # Amazon may block headless requests without a UA

journal:
  pending_folder: "~/Library/Mobile Documents/com~apple~CloudDocs/kindle-journal/pending"
  dry_run: false                  # If true, print title and body to stdout instead of writing file
```

## Build Steps

### 1. Project Scaffolding
- Initialize repo, create directory structure above
- Create and activate venv: `python3 -m venv .venv && source .venv/bin/activate`
- Add `.venv/` to `.gitignore`
- `requirements.txt` dependencies:
  - `imapclient`
  - `python-dotenv`
  - `pyyaml`
  - `requests`
  - `beautifulsoup4` (HTML email body parsing)

### 2. Email Watcher (`watcher/imap_watcher.py`)
- Connect to `imap.gmail.com:993` via SSL using `imapclient`
- Poll `INBOX` on interval
- Search for UNSEEN messages matching `sender_filter` and `subject_filter`
- Yield unread messages as a common `EmailMessage` dataclass:
  ```python
  @dataclass
  class EmailMessage:
      message_id: str
      subject: str
      received_at: datetime
      body_html: str
      body_text: str
  ```
- Do NOT mark as processed here — only mark after full successful pipeline

**Gmail label handling**: After processing, apply the `kindle-processed` label via IMAP and mark as read. Requires the label to exist in Gmail already (create it manually once). This is preferable to moving to a folder — keeps the mail accessible.

### 3. Download Fetcher (`processor/fetch.py`)
- Accept the `EmailMessage`
- Parse `body_html` with BeautifulSoup to find the download links
  - Look for anchor tags with text matching "Download text file" or "Download Searchable PDF"
  - Extract `href` from the preferred format link
- Fetch the URL with `requests.get()`, including a `User-Agent` header
- Return the decoded text string
- Raise on HTTP error or empty response so the caller skips marking the message as processed

**Note on link expiry**: Links expire in 7 days per Amazon. The daemon polls every 60 seconds, so this is not a practical concern as long as the Mac Mini is running. If the daemon was offline for >7 days, the message will be in the inbox but the link will be dead — log a clear error and mark read (won't recover on retry).

### 4. Text Processing (`processor/fetch.py`)
- After fetching the raw text content:
  - Skip line 1 (Kindle page number — discarded, e.g. `Page 24`)
  - Strip leading `# ` from line 2 and use it as the **journal entry title** (e.g. `# 3/22` → `3/22`)
  - Lines 3 onward joined as the **body**
- Strip leading/trailing whitespace from title and body

### 5. iCloud Entry Writer (`journal/icloud_writer.py`)
- Accept `title: str` and `body: str`
- Expand `pending_folder` path and create it if it doesn't exist
- Write a JSON file to the pending folder:
  ```json
  {
    "title": "3/22",
    "body": "-killed it today all day..."
  }
  ```
- Filename: `{timestamp}-entry.json` (e.g. `20260323-143012-entry.json`) to avoid collisions
- If `dry_run` is true, print title and body to stdout instead
- Raise on write failure so the caller skips marking the email as processed

### 6. Main Loop (`main.py`)
- Load config and validate required env vars on startup; fail fast if missing
- Poll loop:
  1. Fetch unseen matching messages
  2. For each message:
     a. Parse and fetch the text file download
     b. Write entry file to iCloud Drive
     c. Apply `kindle-processed` label and mark read
  3. Log each step with timestamp
  4. On fetch/parse exception (step 2a): log error, skip 2b and 2c (message stays unread, retries next poll)
     On expired link specifically: log error, still apply label and mark read (won't recover on retry)
     On file write exception (step 2b): log error, skip step 2c (retries next poll)
  5. Sleep `poll_interval_seconds`

### 7. launchd Service
- `com.chasrogers.kindle-journal.plist` in `~/Library/LaunchAgents/`
- `RunAtLoad: true`, `KeepAlive: true`
- Redirect stdout/stderr to `~/Library/Logs/kindle-journal/`
- Point `ProgramArguments` to the venv Python: `~/Developer/kindle-journal/.venv/bin/python main.py`
- Load with `launchctl load ~/Library/LaunchAgents/com.chasrogers.kindle-journal.plist`

## iOS Shortcut Setup (Manual — Do Before First Run)

The iOS Shortcut watches the iCloud Drive pending folder, reads each JSON file, creates a Journal entry, then deletes the file.

### Create the Shortcut

1. Open **Shortcuts.app** on iPhone/iPad
2. Go to **Automation** tab → **New Automation**
3. Trigger: **Folder** → select `kindle-journal/pending` in iCloud Drive → **A File is Added**
4. Disable "Ask Before Running" so it runs silently
5. Add action: **Get File** — File: the file that was added (Automation input)
6. Add action: **Get Contents of JSON File** — Input: above file → store as `Entry`
7. Add action: **Get Value from Dictionary**
   - Dictionary: `Entry`
   - Key: `title`
   - Store as variable **`Title`**
8. Add action: **Get Value from Dictionary**
   - Dictionary: `Entry`
   - Key: `body`
   - Store as variable **`Body`**
9. Add action: **Create Journal Entry**
   - Title: `Title`
   - Body: `Body`
   - Date: Current Date
10. Add action: **Delete File** — File: the file that was added (same Automation input)
11. Save

### Test Manually

Drop a test JSON file into the iCloud pending folder from Mac:
```bash
mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/kindle-journal/pending
echo '{"title":"Test Entry","body":"This is a test body."}' \
  > ~/Library/Mobile\ Documents/com~apple~CloudDocs/kindle-journal/pending/test-entry.json
```
Wait for the Shortcut to trigger on iPhone and confirm the entry appears in Journal.app. Note: there may be a delay of several minutes before iOS detects the new file.

## Pre-Flight Checklist

- [ ] Gmail App Password created (Google Account → Security → App Passwords)
- [ ] `kindle-processed` label created in Gmail
- [ ] iCloud Drive folder created: `kindle-journal/pending`
- [ ] iOS Shortcut created and file-drop tested
- [ ] `.env` file in place with credentials
- [ ] `dry_run: true` for first real end-to-end test before enabling live file writes

## Out of Scope
- OCR, Vision API, or any image processing (text file makes this unnecessary)
- M365 / Microsoft Graph
- GUI or web interface
- Editing or deleting Journal entries
