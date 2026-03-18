"""Tests for Pydantic response models."""

import pytest
from pydantic import ValidationError

from mcp_granola.models import (
    DataStats,
    ListMeetingsResponse,
    MeetingAttendee,
    MeetingDetails,
    MeetingListItem,
    MeetingPanel,
    SearchResponse,
    SearchResult,
    TranscriptResponse,
    TranscriptSegment,
)


class TestSearchResult:
    def test_valid(self):
        result = SearchResult(
            id="doc-001",
            title="Test Meeting",
            date="2025-01-15",
            score=11.5,
            snippets=["...matched text..."],
        )
        assert result.id == "doc-001"
        assert result.score == 11.5

    def test_empty_snippets(self):
        result = SearchResult(id="doc-001", title="Test", date="2025-01-15", score=1.0, snippets=[])
        assert result.snippets == []

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            SearchResult(id="doc-001", title="Test", date="2025-01-15", snippets=[])  # type: ignore[call-arg]


class TestSearchResponse:
    def test_valid(self):
        resp = SearchResponse(
            query="planning",
            total_results=1,
            results=[
                SearchResult(
                    id="doc-001",
                    title="Q1 Planning",
                    date="2025-01-15",
                    score=10.0,
                    snippets=[],
                )
            ],
        )
        assert resp.total_results == 1
        assert len(resp.results) == 1

    def test_empty_results(self):
        resp = SearchResponse(query="nonexistent", total_results=0, results=[])
        assert resp.results == []


class TestMeetingAttendee:
    def test_valid(self):
        attendee = MeetingAttendee(name="Alice Chen", email="alice@example.com")
        assert attendee.name == "Alice Chen"

    def test_empty_strings(self):
        attendee = MeetingAttendee(name="", email="")
        assert attendee.name == ""


class TestMeetingPanel:
    def test_valid(self):
        panel = MeetingPanel(id="panel-001", title="Action Items", content="Do things")
        assert panel.title == "Action Items"


class TestMeetingDetails:
    def test_valid(self):
        details = MeetingDetails(
            id="doc-001",
            title="Test",
            created_at="2025-01-15T10:00:00Z",
            updated_at=None,
            notes_markdown="# Test",
            notes_plain="Test",
            attendees=[MeetingAttendee(name="Alice", email="alice@example.com")],
            panels=[],
            panels_available=True,
            has_transcript=False,
            transcript_segments=0,
        )
        assert details.updated_at is None
        assert details.has_transcript is False
        assert details.panels_available is True

    def test_with_all_fields(self):
        details = MeetingDetails(
            id="doc-001",
            title="Full Meeting",
            created_at="2025-01-15T10:00:00Z",
            updated_at="2025-01-15T11:00:00Z",
            notes_markdown="# Notes",
            notes_plain="Notes",
            attendees=[
                MeetingAttendee(name="A", email="a@x.com"),
                MeetingAttendee(name="B", email="b@x.com"),
            ],
            panels=[MeetingPanel(id="p1", title="Summary", content="text")],
            panels_available=True,
            has_transcript=True,
            transcript_segments=5,
        )
        assert len(details.attendees) == 2
        assert details.transcript_segments == 5


class TestMeetingListItem:
    def test_valid(self):
        item = MeetingListItem(
            id="doc-001",
            title="Test",
            date="2025-01-15",
            attendee_count=3,
            has_transcript=True,
        )
        assert item.attendee_count == 3


class TestListMeetingsResponse:
    def test_valid(self):
        resp = ListMeetingsResponse(total=1, offset=0, limit=20, meetings=[])
        assert resp.total == 1
        assert resp.meetings == []


class TestTranscriptSegment:
    def test_valid(self):
        seg = TranscriptSegment(
            text="Hello world",
            start_time="00:00:05",
            end_time="00:00:08",
            source="speaker_1",
        )
        assert seg.text == "Hello world"


class TestTranscriptResponse:
    def test_valid(self):
        resp = TranscriptResponse(
            meeting_id="doc-001",
            meeting_title="Test",
            segments=[
                TranscriptSegment(
                    text="Hi", start_time="00:00:00", end_time="00:00:02", source="s1"
                )
            ],
            total_segments=1,
            format="text",
        )
        assert resp.total_segments == 1


class TestDataStats:
    def test_valid(self):
        stats = DataStats(
            total_documents=5,
            total_transcripts=2,
            documents_with_transcripts=2,
            date_range_start="2025-01-15",
            date_range_end="2025-02-15",
            unique_attendees=5,
        )
        assert stats.total_documents == 5

    def test_empty_data(self):
        stats = DataStats(
            total_documents=0,
            total_transcripts=0,
            documents_with_transcripts=0,
            date_range_start="",
            date_range_end="",
            unique_attendees=0,
        )
        assert stats.date_range_start == ""
