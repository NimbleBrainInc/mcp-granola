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

Reads from: `~/Library/Application Support/Granola/cache-v3.json`

Data is cached in memory and auto-refreshes when file changes.

### Structure

```
cache-v3.json
└── cache (JSON string) → parse to:
    └── state
        ├── documents      # dict: {id: Document}
        ├── transcripts    # dict: {doc_id: Segment[]}
        └── documentPanels # dict: {doc_id: {panel_id: Panel}}
```

### Gotchas

- **Nullable fields**: Use `doc.get("field") or ""` not `doc.get("field", "")` (values can be explicit `null`)
- **ProseMirror notes**: Nested structure, use recursive text extraction
- **Sparse transcripts**: Most meetings have privacy mode enabled (only 8 of 478 have transcripts)

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
