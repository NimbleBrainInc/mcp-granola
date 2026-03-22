"""Pydantic models for Granola data and API responses."""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single search result."""

    id: str
    title: str
    date: str
    score: float
    snippets: list[str]


class SearchResponse(BaseModel):
    """Response from search_meetings tool."""

    query: str
    total_results: int
    results: list[SearchResult]


class MeetingAttendee(BaseModel):
    """Meeting attendee information."""

    name: str
    email: str


class MeetingPanel(BaseModel):
    """AI-generated panel/summary."""

    id: str
    title: str
    content: str


class MeetingDetails(BaseModel):
    """Full meeting details."""

    id: str
    title: str
    created_at: str
    updated_at: str | None
    notes_markdown: str
    notes_plain: str
    attendees: list[MeetingAttendee]
    panels: list[MeetingPanel]
    panels_available: bool
    has_transcript: bool
    transcript_segments: int


class MeetingListItem(BaseModel):
    """Summary item for meeting list."""

    id: str
    title: str
    date: str
    attendee_count: int
    has_transcript: bool


class ListMeetingsResponse(BaseModel):
    """Response from list_meetings tool."""

    total: int
    offset: int
    limit: int
    meetings: list[MeetingListItem]


class TranscriptSegment(BaseModel):
    """A single transcript segment."""

    text: str
    start_time: str
    end_time: str
    source: str


class TranscriptResponse(BaseModel):
    """Response from get_transcript tool."""

    meeting_id: str
    meeting_title: str
    segments: list[TranscriptSegment]
    total_segments: int
    format: str


class DataStats(BaseModel):
    """Statistics about the Granola data."""

    total_documents: int
    total_transcripts: int
    documents_with_transcripts: int
    date_range_start: str
    date_range_end: str
    unique_attendees: int


class MeetingSummary(BaseModel):
    """A meeting with notes for summarization."""

    id: str
    title: str
    date: str
    notes_plain: str
    attendees: list[MeetingAttendee]


class SummarizeMeetingsResponse(BaseModel):
    """Response from summarize_meetings tool."""

    total: int
    date_from: str
    date_to: str
    meetings: list[MeetingSummary]


class ActionItem(BaseModel):
    """A single extracted action item."""

    action: str
    meeting_id: str
    meeting_title: str
    meeting_date: str
    source: str


class ActionItemsResponse(BaseModel):
    """Response from extract_action_items tool."""

    total: int
    action_items: list[ActionItem]
