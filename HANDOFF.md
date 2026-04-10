# Kindle → Things Handoff

## What This Does

A daily scheduled Claude agent reads Gmail for Kindle note exports and creates Things tasks — no Python daemon, no iCloud Drive, no iOS Shortcut.

## Prerequisites (verify on iMac before setting up)

1. **Gmail MCP** connected in Claude Desktop (test: ask Claude to get your Gmail profile)
2. **Things MCP** connected in Claude Desktop (test: ask Claude to get today's tasks)

## Setup

In Claude Desktop on the iMac, run:

```
/schedule
```

Choose a daily time (e.g. 8:00 AM), then use this as the agent prompt:

---

**Agent prompt:**

```
Check Gmail for unread emails from do-not-reply@amazon.com where the subject contains "You sent a file" and "from your Kindle".

For each matching email:
1. Extract the notebook name from the subject line — it's in quotes, e.g. "Journal" from the subject "You sent a file "Journal" from your Kindle"
2. Read the email body and find the "Download text file" link
3. Download the file using curl in Bash (include a User-Agent header: Mozilla/5.0)
4. Parse the downloaded text:
   - Skip line 1 (it's a page number)
   - Line 2 is the note title (strip leading "# " and whitespace)
   - Lines 3 onwards are the body
5. Create a Things task:
   - Title: "[NotebookName] Entry" (e.g. "Journal Entry")
   - Notes: the full parsed body text
6. Mark the Gmail email as read

If there are no matching unread emails, do nothing and report that.
```

---

## Notes

- The download links expire in 7 days, so daily is fine
- The notebook name comes from the email subject, not the downloaded file
- The Gmail account is ntwkrgr@gmail.com
- The Python code in this repo is obsolete for this flow — ignore it
