# Granola MCP Server

MCP server for searching and extracting information from local Granola meeting notes.

## Architecture

```
src/mcp_granola/
├── server.py   # MCP tools (FastMCP) + stdio entrypoint
├── data.py     # Data loader with caching and search
└── models.py   # Pydantic response models
```

## Data Source

Auto-detects the newest Granola cache file from `~/Library/Application Support/Granola/`:
- Tries `cache-v6.json`, `cache-v5.json`, `cache-v4.json`, `cache-v3.json` in order
- Uses the first file that exists

Data is cached in memory and auto-refreshes when file changes.

### Structure

```
cache-vN.json
└── cache (v3: JSON string, v4+: dict) → normalize to:
    └── state
        ├── documents      # dict: {id: Document}
        ├── transcripts    # dict: {doc_id: Segment[]}
        └── documentPanels # dict: {doc_id: {panel_id: Panel}} — v3 only, removed in v6
```

### Version Differences

| Feature | v3 | v6 |
|---------|----|----|
| `cache` field | JSON string | dict |
| `documentPanels` | Present | Removed |
| `notes` (ProseMirror) | Not present | Present on most docs |
| `notes_plain` | Populated | Partially populated (~77%) |
| `summary`/`overview` | Populated | Empty (moved server-side) |
| People `details` | Not present | Enriched (employment, company, avatar) |

### Gotchas

- **Nullable fields**: Use `doc.get("field") or ""` not `doc.get("field", "")` (values can be explicit `null`)
- **ProseMirror notes**: When `notes_plain` is empty, text is auto-extracted from ProseMirror `notes` field
- **Sparse transcripts**: Most meetings have privacy mode enabled (only 8 of 478 have transcripts)
- **Panels**: `panels_available` field in `MeetingDetails` indicates whether the cache version includes panel data

## Commands

```bash
uv run pytest           # Test
uv run ruff format .    # Format
uv run ruff check .     # Lint
uv run ty check src/    # Type check
```

## Local Testing

```bash
# Run directly
uv run python -m mcp_granola.server

# With mpak (after bundling)
mpak bundle run @nimblebraininc/granola
```

## Tools

| Tool | Description |
|------|-------------|
| `search_meetings` | Full-text search with date/attendee filters |
| `get_meeting` | Get full document with notes and panels |
| `list_meetings` | Browse meetings with pagination |
| `search_by_person` | Find meetings with specific person |
| `get_transcript` | Get raw transcript segments |
| `get_meeting_stats` | Data statistics |
| `summarize_meetings` | Summarize meetings over a time period (with notes + attendees) |
| `extract_action_items` | Extract action items/TODOs from meetings |
