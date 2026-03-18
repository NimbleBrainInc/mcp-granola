# Granola MCP Server — Skill Guide

## Tools

| Tool | Use when... |
|------|-------------|
| `list_meetings` | You need to browse recent meetings or paginate through history |
| `search_meetings` | You have a keyword or phrase to search across all meeting notes |
| `search_by_person` | You want all meetings involving a specific person (by name or email) |
| `get_meeting` | You have a `meeting_id` and need the full notes, attendees, and panels |
| `get_transcript` | You need the raw transcript segments for a specific meeting |
| `get_meeting_stats` | You need an overview of how much data is available |

## Parameter Reference

All tools that accept meeting identifiers use `meeting_id` (not `doc_id`, `id`, or `document_id`). The `meeting_id` value comes from the `id` field in search results and meeting lists.

## Context Reuse

- Use `id` from `list_meetings` or `search_meetings` results as the `meeting_id` parameter for `get_meeting` and `get_transcript`
- Use `has_transcript` from meeting lists to decide whether calling `get_transcript` will return data
- Use `attendee_count` from meeting lists to gauge meeting size before fetching full details

## Workflows

### 1. Summarize a Meeting with a Specific Person
1. `search_by_person` with their name to find meetings
2. Pick the relevant meeting by title/date
3. `get_meeting` with `meeting_id` to get notes and panels
4. If notes are sparse and `has_transcript` is true: `get_transcript` with `meeting_id`

### 2. Find and Review a Topic
1. `search_meetings` with keywords (e.g., "pricing", "roadmap")
2. Review snippets in results to find the right meeting
3. `get_meeting` with `meeting_id` for full context

### 3. Browse Recent Activity
1. `list_meetings` with default sort (newest first)
2. Filter by date range or attendee if needed
3. `get_meeting` on items of interest

### 4. Get Transcript for Deep Review
1. Find the meeting via search or list
2. Check `has_transcript` — most meetings have privacy mode enabled and won't have transcripts
3. `get_transcript` with `meeting_id` and `format="timestamped"` for timing info

## Tips

- **Transcript availability is rare**: Most Granola meetings use privacy mode. Check `has_transcript` before attempting `get_transcript`.
- **`get_meeting` with `include_transcript=True`**: Appends the transcript to the notes in a single call — useful when you want everything at once without a separate `get_transcript` call.
- **Date filters**: Use `YYYY-MM-DD` format for `date_from` and `date_to` parameters.
- **Attendee filter**: Works on both name and email — partial matches are supported.
