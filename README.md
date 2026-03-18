# Granola MCP Server

[![CI](https://github.com/NimbleBrainInc/mcp-granola/actions/workflows/ci.yml/badge.svg)](https://github.com/NimbleBrainInc/mcp-granola/actions/workflows/ci.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![MCPB](https://img.shields.io/badge/mcpb-v0.3-purple.svg)](https://github.com/modelcontextprotocol/mcpb)
[![mpak](https://img.shields.io/badge/mpak-@nimblebraininc/granola-orange.svg)](https://mpak.dev)

MCP server for searching your local [Granola](https://granola.ai) meeting notes.

- Search across notes, titles, and AI summaries
- Filter by date range or attendee
- Pull transcripts when available
- Read AI panels (summaries, action items) when available
- Supports Granola cache v3 through v6
- Reloads automatically when Granola updates its cache

## Installation

### With mpak

```bash
mpak bundle run @nimblebraininc/granola
```

### Local Development

```bash
uv sync --dev
uv run python -m mcp_granola.server
```

## Tools

| Tool                | Description                                                 |
| ------------------- | ----------------------------------------------------------- |
| `search_meetings`   | Search notes by keyword with optional date/attendee filters |
| `get_meeting`       | Get full meeting details including notes and AI panels      |
| `list_meetings`     | List meetings with pagination and filtering                 |
| `search_by_person`  | Find all meetings with a specific person                    |
| `get_transcript`    | Get transcript segments with timestamps                     |
| `get_meeting_stats` | Get statistics about your meeting data                      |

## Data Source

Auto-detects the newest Granola cache file (`cache-v6.json` through `cache-v3.json`) from `~/Library/Application Support/Granola/` (macOS only). Cached in memory, reloads when the file changes.

## Development

```bash
make check          # Run all checks (format, lint, typecheck, test)
make test           # Run tests
make test-cov       # Run tests with coverage
make format         # Format code
make lint           # Lint code
make typecheck      # Type check with ty
```

## License

MIT
