"""Granola MCP Server - Search and extract from meeting notes."""

from datetime import date, timedelta
from importlib.resources import files

from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .data import get_data
from .models import (
    ActionItem,
    ActionItemsResponse,
    DataStats,
    ListMeetingsResponse,
    MeetingAttendee,
    MeetingDetails,
    MeetingListItem,
    MeetingPanel,
    MeetingSummary,
    SearchResponse,
    SearchResult,
    SummarizeMeetingsResponse,
    TranscriptResponse,
    TranscriptSegment,
)

# Create MCP server
mcp = FastMCP(
    "Granola",
    instructions=(
        "Before using tools, read the skill://granola/usage resource "
        "for tool selection guidance and parameter reference."
    ),
)

SKILL_CONTENT = files("mcp_granola").joinpath("SKILL.md").read_text()


def _resolve_days(days: int) -> tuple[str, str]:
    """Convert 'last N days' into (date_from, date_to) ISO date strings."""
    today = date.today()
    return (today - timedelta(days=days)).isoformat(), today.isoformat()


@mcp.resource("skill://granola/usage")
def granola_skill() -> str:
    """How to effectively use this server's tools."""
    return SKILL_CONTENT


# Health endpoint for HTTP transport
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    return JSONResponse({"status": "healthy", "service": "mcp-granola"})


@mcp.tool()
async def search_meetings(
    query: str,
    limit: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
    attendee: str | None = None,
    ctx: Context | None = None,
) -> SearchResponse:
    """Search meeting notes by keyword or phrase.

    Args:
        query: Search query (keywords or phrase)
        limit: Maximum results to return (default: 10)
        date_from: Filter by start date (YYYY-MM-DD)
        date_to: Filter by end date (YYYY-MM-DD)
        attendee: Filter by attendee name or email
        ctx: MCP context

    Returns:
        Search results with matching documents
    """
    if ctx:
        await ctx.info(f"Searching meetings for: {query}")

    data = get_data()
    results = data.search(
        query=query,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        attendee=attendee,
    )

    return SearchResponse(
        query=query,
        total_results=len(results),
        results=[
            SearchResult(
                id=r["id"],
                title=r["title"],
                date=r["date"],
                score=r["score"],
                snippets=r["snippets"],
            )
            for r in results
        ],
    )


@mcp.tool()
async def get_meeting(
    meeting_id: str,
    include_transcript: bool = False,
    ctx: Context | None = None,
) -> MeetingDetails | str:
    """Get complete meeting details including notes and summaries.

    Args:
        meeting_id: Meeting document ID
        include_transcript: Include full transcript in notes_plain field
        ctx: MCP context

    Returns:
        Full meeting details with notes, attendees, and AI panels
    """
    if ctx:
        await ctx.info(f"Getting meeting: {meeting_id}")

    data = get_data()
    doc = data.get_document(meeting_id)

    if not doc:
        return f"Meeting not found: {meeting_id}"

    # Optionally append transcript to notes
    notes_plain = doc["notes_plain"]
    if include_transcript and doc["has_transcript"]:
        transcript_data = data.get_transcript(meeting_id)
        if transcript_data and transcript_data["segments"]:
            transcript_text = "\n\n--- TRANSCRIPT ---\n\n"
            for seg in transcript_data["segments"]:
                transcript_text += f"{seg['text']}\n"
            notes_plain += transcript_text

    return MeetingDetails(
        id=doc["id"],
        title=doc["title"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        notes_markdown=doc["notes_markdown"],
        notes_plain=notes_plain,
        attendees=[MeetingAttendee(name=a["name"], email=a["email"]) for a in doc["attendees"]],
        panels=[
            MeetingPanel(id=p["id"], title=p["title"], content=p["content"]) for p in doc["panels"]
        ],
        panels_available=doc["panels_available"],
        has_transcript=doc["has_transcript"],
        transcript_segments=doc["transcript_segments"],
    )


@mcp.tool()
async def list_meetings(
    limit: int = 20,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    attendee: str | None = None,
    sort: str = "date_desc",
    ctx: Context | None = None,
) -> ListMeetingsResponse:
    """List meetings with optional filters.

    Args:
        limit: Maximum results (default: 20)
        offset: Skip first N results
        date_from: Filter by start date (YYYY-MM-DD)
        date_to: Filter by end date (YYYY-MM-DD)
        attendee: Filter by attendee name or email
        sort: Sort order - date_desc, date_asc, or title
        ctx: MCP context

    Returns:
        Paginated list of meetings
    """
    if ctx:
        await ctx.info(f"Listing meetings (limit={limit}, offset={offset})")

    data = get_data()
    total, items = data.list_documents(
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
        attendee=attendee,
        sort=sort,
    )

    return ListMeetingsResponse(
        total=total,
        offset=offset,
        limit=limit,
        meetings=[
            MeetingListItem(
                id=item["id"],
                title=item["title"],
                date=item["date"],
                attendee_count=item["attendee_count"],
                has_transcript=item["has_transcript"],
            )
            for item in items
        ],
    )


@mcp.tool()
async def search_by_person(
    person: str,
    limit: int = 20,
    date_from: str | None = None,
    date_to: str | None = None,
    ctx: Context | None = None,
) -> ListMeetingsResponse:
    """Find all meetings involving a specific person.

    Args:
        person: Person's name or email address
        limit: Maximum results (default: 20)
        date_from: Filter by start date (YYYY-MM-DD)
        date_to: Filter by end date (YYYY-MM-DD)
        ctx: MCP context

    Returns:
        List of meetings with that person
    """
    if ctx:
        await ctx.info(f"Searching meetings with: {person}")

    data = get_data()
    items = data.search_by_person(person=person, limit=limit, date_from=date_from, date_to=date_to)

    return ListMeetingsResponse(
        total=len(items),
        offset=0,
        limit=limit,
        meetings=[
            MeetingListItem(
                id=item["id"],
                title=item["title"],
                date=item["date"],
                attendee_count=item["attendee_count"],
                has_transcript=item["has_transcript"],
            )
            for item in items
        ],
    )


@mcp.tool()
async def get_transcript(
    meeting_id: str,
    format: str = "text",
    ctx: Context | None = None,
) -> TranscriptResponse | str:
    """Get the full transcript for a meeting.

    Args:
        meeting_id: Meeting document ID
        format: Output format - text or timestamped
        ctx: MCP context

    Returns:
        Transcript segments with timing information
    """
    if ctx:
        await ctx.info(f"Getting transcript for: {meeting_id}")

    data = get_data()
    result = data.get_transcript(meeting_id, format=format)

    if not result:
        return f"Meeting not found: {meeting_id}"

    if not result["segments"]:
        return f"No transcript available for meeting: {result['meeting_title']}"

    return TranscriptResponse(
        meeting_id=result["meeting_id"],
        meeting_title=result["meeting_title"],
        segments=[
            TranscriptSegment(
                text=s["text"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                source=s["source"],
            )
            for s in result["segments"]
        ],
        total_segments=result["total_segments"],
        format=result["format"],
    )


@mcp.tool()
async def summarize_meetings(
    date_from: str | None = None,
    date_to: str | None = None,
    days: int | None = None,
    person: str | None = None,
    ctx: Context | None = None,
) -> SummarizeMeetingsResponse:
    """Get meeting summaries with notes for a time period.

    Use this when asked to summarize, recap, or review meetings over a period.
    Provide either date_from/date_to (YYYY-MM-DD) or days (last N days).

    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        days: Convenience shortcut: last N days from today
        person: Filter by attendee name or email
        ctx: MCP context

    Returns:
        Meetings with their notes and attendees
    """
    if date_from or date_to:
        if not date_from:
            date_from = "2000-01-01"
        if not date_to:
            date_to = date.today().isoformat()
    elif days is not None:
        date_from, date_to = _resolve_days(days)
    else:
        date_from, date_to = _resolve_days(7)

    if ctx:
        await ctx.info(f"Summarizing meetings from {date_from} to {date_to}")

    data = get_data()
    results = data.get_meeting_summaries(date_from=date_from, date_to=date_to, person=person)

    return SummarizeMeetingsResponse(
        total=len(results),
        date_from=date_from,
        date_to=date_to,
        meetings=[
            MeetingSummary(
                id=r["id"],
                title=r["title"],
                date=r["date"],
                notes_plain=r["notes_plain"],
                attendees=[
                    MeetingAttendee(name=a["name"], email=a["email"]) for a in r["attendees"]
                ],
            )
            for r in results
        ],
    )


@mcp.tool()
async def extract_action_items(
    meeting_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int | None = None,
    person: str | None = None,
    ctx: Context | None = None,
) -> ActionItemsResponse:
    """Extract action items from meeting notes.

    Use this when asked for action items, TODOs, or next steps.
    Can target a single meeting by ID, or scan multiple meetings by date range.

    Args:
        meeting_id: Specific meeting ID to extract from (takes precedence)
        date_from: Start date (YYYY-MM-DD) for scanning multiple meetings
        date_to: End date (YYYY-MM-DD) for scanning multiple meetings
        days: Convenience shortcut: last N days from today
        person: Filter by attendee name or email (only with date range)
        ctx: MCP context

    Returns:
        Extracted action items with source meeting context
    """
    if not meeting_id:
        if date_from or date_to:
            if not date_from:
                date_from = "2000-01-01"
            if not date_to:
                date_to = date.today().isoformat()
        elif days is not None:
            date_from, date_to = _resolve_days(days)
        else:
            date_from, date_to = _resolve_days(7)

    if ctx:
        if meeting_id:
            await ctx.info(f"Extracting action items from meeting: {meeting_id}")
        else:
            await ctx.info(f"Extracting action items from {date_from} to {date_to}")

    data = get_data()
    items = data.extract_action_items(
        meeting_id=meeting_id,
        date_from=date_from,
        date_to=date_to,
        person=person,
    )

    return ActionItemsResponse(
        total=len(items),
        action_items=[
            ActionItem(
                action=item["action"],
                meeting_id=item["meeting_id"],
                meeting_title=item["meeting_title"],
                meeting_date=item["meeting_date"],
                source=item["source"],
            )
            for item in items
        ],
    )


@mcp.tool()
async def get_meeting_stats(ctx: Context | None = None) -> DataStats:
    """Get statistics about your Granola meeting data.

    Args:
        ctx: MCP context

    Returns:
        Statistics including document counts, date range, and unique attendees
    """
    if ctx:
        await ctx.info("Getting meeting stats")

    data = get_data()
    stats = data.get_stats()

    return DataStats(
        total_documents=stats["total_documents"],
        total_transcripts=stats["total_transcripts"],
        documents_with_transcripts=stats["documents_with_transcripts"],
        date_range_start=stats["date_range_start"],
        date_range_end=stats["date_range_end"],
        unique_attendees=stats["unique_attendees"],
    )


# Create ASGI application for HTTP deployment
app = mcp.http_app()


# Stdio entrypoint for Claude Desktop / mpak
if __name__ == "__main__":
    mcp.run()
