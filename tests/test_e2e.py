"""End-to-end tests: full round-trip through the data layer and MCP tools."""

import json

import pytest
from fastmcp import Client


def _extract_text(result) -> str:
    """Extract text content from a CallToolResult."""
    if hasattr(result, "content"):
        # CallToolResult with content list
        for item in result.content:
            if hasattr(item, "text"):
                return item.text
    # Fallback: try indexing (older API)
    if isinstance(result, list):
        return result[0].text if hasattr(result[0], "text") else str(result[0])
    return str(result)


class TestE2ESearchToDetail:
    """Search for a meeting, then retrieve its full details and transcript."""

    @pytest.mark.asyncio
    async def test_search_then_get_meeting(self, mcp_server):
        async with Client(mcp_server) as client:
            search_result = await client.call_tool("search_meetings", {"query": "API"})
            search_data = json.loads(_extract_text(search_result))
            assert search_data["total_results"] >= 1

            meeting_id = search_data["results"][0]["id"]
            meeting_result = await client.call_tool("get_meeting", {"meeting_id": meeting_id})
            meeting_data = json.loads(_extract_text(meeting_result))
            assert meeting_data["title"] == "API Architecture Discussion"
            assert len(meeting_data["attendees"]) >= 2

    @pytest.mark.asyncio
    async def test_search_then_get_transcript(self, mcp_server):
        async with Client(mcp_server) as client:
            search_result = await client.call_tool("search_meetings", {"query": "Q1 Planning"})
            search_data = json.loads(_extract_text(search_result))
            meeting_id = search_data["results"][0]["id"]

            transcript_result = await client.call_tool("get_transcript", {"meeting_id": meeting_id})
            transcript_data = json.loads(_extract_text(transcript_result))
            assert transcript_data["total_segments"] == 3
            assert "Q1 priorities" in transcript_data["segments"][0]["text"]


class TestE2EPersonWorkflow:
    """Find a person's meetings, then drill into details."""

    @pytest.mark.asyncio
    async def test_person_to_meeting_details(self, mcp_server):
        async with Client(mcp_server) as client:
            person_result = await client.call_tool("search_by_person", {"person": "Carol"})
            person_data = json.loads(_extract_text(person_result))
            assert person_data["total"] >= 2

            meeting_id = person_data["meetings"][0]["id"]
            meeting_result = await client.call_tool("get_meeting", {"meeting_id": meeting_id})
            meeting_data = json.loads(_extract_text(meeting_result))
            attendee_names = [a["name"] for a in meeting_data["attendees"]]
            assert "Carol Davis" in attendee_names


class TestE2EStatsAccuracy:
    """Verify stats match known fixture data."""

    @pytest.mark.asyncio
    async def test_stats_match_fixture(self, mcp_server):
        async with Client(mcp_server) as client:
            stats_result = await client.call_tool("get_meeting_stats", {})
            stats_data = json.loads(_extract_text(stats_result))

            assert stats_data["total_documents"] == 5
            assert stats_data["documents_with_transcripts"] == 2
            assert stats_data["date_range_start"] == "2025-01-15"
            assert stats_data["date_range_end"] == "2025-02-15"

    @pytest.mark.asyncio
    async def test_list_total_matches_stats(self, mcp_server):
        """List total should match stats total_documents."""
        async with Client(mcp_server) as client:
            stats_result = await client.call_tool("get_meeting_stats", {})
            stats_data = json.loads(_extract_text(stats_result))

            list_result = await client.call_tool("list_meetings", {"limit": 100})
            list_data = json.loads(_extract_text(list_result))

            assert list_data["total"] == stats_data["total_documents"]


class TestE2EPaginationConsistency:
    """Verify pagination returns all items across pages."""

    @pytest.mark.asyncio
    async def test_all_pages_cover_total(self, mcp_server):
        async with Client(mcp_server) as client:
            full_result = await client.call_tool("list_meetings", {"limit": 100})
            full_data = json.loads(_extract_text(full_result))
            total = full_data["total"]

            all_ids = set()
            offset = 0
            while offset < total:
                page_result = await client.call_tool(
                    "list_meetings", {"limit": 2, "offset": offset}
                )
                page_data = json.loads(_extract_text(page_result))
                for m in page_data["meetings"]:
                    all_ids.add(m["id"])
                offset += 2

            assert len(all_ids) == total
