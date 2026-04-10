# Kindle → Things Handoff

## What This Does

A daily scheduled Claude agent reads Gmail for Kindle note exports and creates Things tasks — no Python daemon, no iCloud Drive, no iOS Shortcut.

The full flow is packaged as a skill: **`kindle-to-things`**
(`~/.claude/skills/kindle-to-things/SKILL.md`).

## Prerequisites (verify on iMac before setting up)

1. **Gmail MCP** connected in Claude Desktop (test: ask Claude to get your Gmail profile)
2. **Things MCP** connected in Claude Desktop (test: ask Claude to get today's tasks)

## Setup

In Claude Desktop on the iMac, run:

```
/schedule
```

Choose a daily time (e.g. 8:00 AM), and use this as the agent prompt:

```
Run the kindle-to-things skill.
```

That's it. All procedural details (Gmail query, download, parse, Things task creation,
retry-safe ordering, failure modes) live inside the skill so they stay in one place.

## Manual Run

At any time, in Claude Desktop, you can say:

- "check my Kindle"
- "run the kindle-to-things skill"
- "import any new Kindle notes"

…and the skill will trigger on demand.

## Notes

- Download links in the Amazon email expire in 7 days, so daily polling is fine.
- The notebook name comes from the email subject, not the downloaded file.
- The Gmail account is `ntwkrgr@gmail.com`.
- The previous Python daemon implementation has been removed from this repo.
  Everything now runs inside Claude Desktop via the skill + MCPs.
