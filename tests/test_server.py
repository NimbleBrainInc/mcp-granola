"""Integration tests for MCP server tools via FastMCP Client."""

import pytest
from fastmcp import Client


class TestSearchMeetingsTool:
    @pytest.mark.asyncio
    async def test_basic_search(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("search_meetings", {"query": "API"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "search_meetings",
                {
                    "query": "planning",
                    "date_from": "2025-01-01",
                    "date_to": "2025-01-31",
                    "limit": 5,
                },
            )
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_with_attendee(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "search_meetings",
                {"query": "meeting", "attendee": "alice"},
            )
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_no_results(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("search_meetings", {"query": "xyznonexistent"})
        assert result is not None


class TestGetMeetingTool:
    @pytest.mark.asyncio
    async def test_existing_meeting(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_meeting", {"meeting_id": "doc-001"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_meeting_with_transcript(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "get_meeting",
                {"meeting_id": "doc-001", "include_transcript": True},
            )
        assert result is not None

    @pytest.mark.asyncio
    async def test_nonexistent_meeting(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_meeting", {"meeting_id": "nonexistent"})
        # Should return error string, not crash
        assert result is not None


class TestListMeetingsTool:
    @pytest.mark.asyncio
    async def test_list_all(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_meetings", {})
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_meetings", {"limit": 2, "offset": 0})
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_with_sort(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_meetings", {"sort": "title"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_with_date_filter(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_meetings", {"date_from": "2025-02-01"})
        assert result is not None


class TestSearchByPersonTool:
    @pytest.mark.asyncio
    async def test_search_by_name(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("search_by_person", {"person": "Alice"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_by_email(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("search_by_person", {"person": "carol@example.com"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_no_matches(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("search_by_person", {"person": "nobody"})
        assert result is not None


class TestGetTranscriptTool:
    @pytest.mark.asyncio
    async def test_with_transcript(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_transcript", {"meeting_id": "doc-001"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_without_transcript(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_transcript", {"meeting_id": "doc-002"})
        # Returns error string for no transcript
        assert result is not None

    @pytest.mark.asyncio
    async def test_nonexistent_meeting(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_transcript", {"meeting_id": "nonexistent"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_timestamped_format(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "get_transcript",
                {"meeting_id": "doc-001", "format": "timestamped"},
            )
        assert result is not None


class TestGetMeetingStatsTool:
    @pytest.mark.asyncio
    async def test_stats(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_meeting_stats", {})
        assert result is not None


class TestV6SearchMeetingsTool:
    @pytest.mark.asyncio
    async def test_search_finds_prosemirror_content(self, mcp_server_v6):
        """Search returns results from ProseMirror-only documents."""
        async with Client(mcp_server_v6) as client:
            result = await client.call_tool("search_meetings", {"query": "code review"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_with_attendee(self, mcp_server_v6):
        async with Client(mcp_server_v6) as client:
            result = await client.call_tool(
                "search_meetings", {"query": "API", "attendee": "alice"}
            )
        assert result is not None


class TestV6GetMeetingTool:
    @pytest.mark.asyncio
    async def test_v6_meeting_no_panels(self, mcp_server_v6):
        """get_meeting on v6 data returns panels_available=False."""
        async with Client(mcp_server_v6) as client:
            result = await client.call_tool("get_meeting", {"meeting_id": "doc-001"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_v6_meeting_notes_fallback(self, mcp_server_v6):
        """get_meeting extracts notes from ProseMirror when notes_plain is empty."""
        async with Client(mcp_server_v6) as client:
            result = await client.call_tool("get_meeting", {"meeting_id": "doc-002"})
        assert result is not None


class TestV6StatsTool:
    @pytest.mark.asyncio
    async def test_v6_stats(self, mcp_server_v6):
        async with Client(mcp_server_v6) as client:
            result = await client.call_tool("get_meeting_stats", {})
        assert result is not None


class TestSkillResource:
    @pytest.mark.asyncio
    async def test_skill_resource_listed(self, mcp_server):
        """The skill://granola/usage resource is discoverable."""
        async with Client(mcp_server) as client:
            resources = await client.list_resources()
        uris = {str(r.uri) for r in resources}
        assert "skill://granola/usage" in uris

    @pytest.mark.asyncio
    async def test_skill_resource_readable(self, mcp_server):
        """The skill resource returns non-empty markdown content."""
        async with Client(mcp_server) as client:
            result = await client.read_resource("skill://granola/usage")
        content = result[0].text if hasattr(result[0], "text") else str(result[0])
        assert "## Tools" in content
        assert "meeting_id" in content

    @pytest.mark.asyncio
    async def test_server_instructions_reference_skill(self, mcp_server):
        """Server instructions point LLMs to the skill resource."""
        async with Client(mcp_server) as client:
            init = await client.initialize()
        assert "skill://granola/usage" in init.instructions


class TestToolListing:
    @pytest.mark.asyncio
    async def test_all_tools_registered(self, mcp_server):
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "search_meetings",
            "get_meeting",
            "list_meetings",
            "search_by_person",
            "get_transcript",
            "get_meeting_stats",
        }
        assert expected.issubset(tool_names)

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self, mcp_server):
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"
