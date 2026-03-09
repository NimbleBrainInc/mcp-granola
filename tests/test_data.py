"""Tests for the GranolaData data layer."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

from mcp_granola.data import GranolaData, get_data


class TestGranolaSingleton:
    def test_singleton_returns_same_instance(self):
        a = GranolaData()
        b = GranolaData()
        assert a is b

    def test_get_data_returns_singleton(self):
        instance = get_data()
        assert isinstance(instance, GranolaData)
        assert get_data() is instance


class TestDataLoading:
    def test_load_from_fixture(self, granola_data: GranolaData):
        assert len(granola_data.documents) == 5

    def test_documents_have_required_fields(self, granola_data: GranolaData):
        doc = granola_data.documents["doc-001"]
        assert "title" in doc
        assert "created_at" in doc
        assert "people" in doc

    def test_transcripts_loaded(self, granola_data: GranolaData):
        assert "doc-001" in granola_data.transcripts
        assert "doc-004" in granola_data.transcripts
        assert len(granola_data.transcripts["doc-001"]) == 3

    def test_panels_loaded(self, granola_data: GranolaData):
        assert "doc-001" in granola_data.panels
        assert "panel-001" in granola_data.panels["doc-001"]

    def test_missing_file_returns_empty(self):
        """When the Granola cache file doesn't exist, properties return empty."""
        import mcp_granola.data as data_module

        original = data_module.GRANOLA_PATH
        try:
            data_module.GRANOLA_PATH = Path("/nonexistent/path.json")
            data = GranolaData()
            data._data = None
            data._last_modified = None
            # _needs_reload returns False for missing file, so _load returns {}
            assert data.documents == {}
            assert data.transcripts == {}
            assert data.panels == {}
        finally:
            data_module.GRANOLA_PATH = original

    def test_reload_on_file_change(self, granola_data: GranolaData):
        """Changing mtime triggers reload detection."""
        granola_data._last_modified = 0.0  # Old mtime
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_mtime = 999.0
                assert granola_data._needs_reload() is True


class TestAttendeeExtraction:
    def test_extracts_creator_and_attendees(self, granola_data: GranolaData):
        doc = granola_data.documents["doc-001"]
        attendees = granola_data._get_attendees(doc)
        emails = {a["email"] for a in attendees}
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails
        assert "carol@example.com" in emails
        assert len(attendees) == 3

    def test_empty_people(self, granola_data: GranolaData):
        doc: dict[str, Any] = {"people": {}}
        attendees = granola_data._get_attendees(doc)
        assert attendees == []

    def test_missing_people(self, granola_data: GranolaData):
        doc: dict[str, Any] = {}
        attendees = granola_data._get_attendees(doc)
        assert attendees == []


class TestProseMirrorExtraction:
    def test_plain_text_node(self, granola_data: GranolaData):
        node = {"type": "text", "text": "Hello"}
        assert granola_data._extract_prosemirror_text(node) == "Hello"

    def test_paragraph(self, granola_data: GranolaData):
        node = {
            "type": "paragraph",
            "content": [{"type": "text", "text": "A sentence."}],
        }
        result = granola_data._extract_prosemirror_text(node)
        assert "A sentence." in result

    def test_bullet_list(self, granola_data: GranolaData):
        node = {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Item one"}],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Item two"}],
                        }
                    ],
                },
            ],
        }
        result = granola_data._extract_prosemirror_text(node)
        assert "- Item one" in result
        assert "- Item two" in result

    def test_nested_doc(self, granola_data: GranolaData):
        node = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "First para"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Second para"}],
                },
            ],
        }
        result = granola_data._extract_prosemirror_text(node)
        assert "First para" in result
        assert "Second para" in result

    def test_empty_node(self, granola_data: GranolaData):
        node: dict[str, Any] = {"type": "doc", "content": []}
        result = granola_data._extract_prosemirror_text(node)
        assert result == ""

    def test_real_panel_extraction(self, granola_data: GranolaData):
        """Extract text from actual fixture panel content."""
        panel = granola_data.panels["doc-001"]["panel-001"]
        text = granola_data._extract_panel_text(panel["content"])
        assert "Launch API by end of Q1" in text
        assert "Post job listings" in text


class TestSearch:
    def test_basic_search(self, granola_data: GranolaData):
        results = granola_data.search("API")
        assert len(results) >= 1
        titles = [r["title"] for r in results]
        assert "API Architecture Discussion" in titles

    def test_search_scores_title_higher(self, granola_data: GranolaData):
        results = granola_data.search("planning")
        assert results[0]["title"] == "Q1 Planning Session"

    def test_search_case_insensitive(self, granola_data: GranolaData):
        upper = granola_data.search("API")
        lower = granola_data.search("api")
        assert len(upper) == len(lower)

    def test_search_with_limit(self, granola_data: GranolaData):
        results = granola_data.search("the", limit=2)
        assert len(results) <= 2

    def test_search_no_results(self, granola_data: GranolaData):
        results = granola_data.search("xyznonexistent")
        assert results == []

    def test_search_with_date_filter(self, granola_data: GranolaData):
        results = granola_data.search("", date_from="2025-02-01")
        for r in results:
            assert r["date"] >= "2025-02-01"

    def test_search_with_date_range(self, granola_data: GranolaData):
        results = granola_data.search("meeting", date_from="2025-01-01", date_to="2025-01-31")
        for r in results:
            assert "2025-01" in r["date"]

    def test_search_with_attendee_filter(self, granola_data: GranolaData):
        results = granola_data.search("", attendee="carol")
        for r in results:
            # Verify Carol is actually in each result's doc
            doc = granola_data.get_document(r["id"])
            assert doc is not None
            attendee_names = [a["name"].lower() for a in doc["attendees"]]
            attendee_emails = [a["email"].lower() for a in doc["attendees"]]
            assert any("carol" in n for n in attendee_names) or any(
                "carol" in e for e in attendee_emails
            )

    def test_search_snippets(self, granola_data: GranolaData):
        results = granola_data.search("onboarding")
        matching = [r for r in results if r["snippets"]]
        assert len(matching) >= 1

    def test_search_cache_invalidation(self, granola_data: GranolaData):
        """Search cache is rebuilt after data change."""
        granola_data.search("test")
        assert granola_data._search_cache is not None
        granola_data._search_cache = None
        granola_data.search("test")
        assert granola_data._search_cache is not None


class TestSnippetExtraction:
    def test_snippet_with_match(self, granola_data: GranolaData):
        text = "This is a long text with the keyword somewhere in the middle of it all."
        snippet = granola_data._extract_snippet(text, "keyword", context=10)
        assert "keyword" in snippet

    def test_snippet_no_match(self, granola_data: GranolaData):
        text = "Short text here"
        snippet = granola_data._extract_snippet(text, "missing")
        assert snippet == "Short text here"

    def test_snippet_truncation(self, granola_data: GranolaData):
        text = "x" * 300
        snippet = granola_data._extract_snippet(text, "nomatch")
        assert snippet.endswith("...")
        assert len(snippet) <= 204  # 200 + "..."

    def test_snippet_with_ellipsis(self, granola_data: GranolaData):
        text = "A" * 200 + "MATCH" + "B" * 200
        snippet = granola_data._extract_snippet(text, "MATCH", context=20)
        assert snippet.startswith("...")
        assert snippet.endswith("...")
        assert "MATCH" in snippet


class TestGetDocument:
    def test_existing_document(self, granola_data: GranolaData):
        doc = granola_data.get_document("doc-001")
        assert doc is not None
        assert doc["title"] == "Q1 Planning Session"
        assert doc["has_transcript"] is True
        assert doc["transcript_segments"] == 3
        assert len(doc["attendees"]) == 3

    def test_document_with_panels(self, granola_data: GranolaData):
        doc = granola_data.get_document("doc-001")
        assert doc is not None
        assert len(doc["panels"]) == 2
        panel_titles = [p["title"] for p in doc["panels"]]
        assert "Action Items" in panel_titles

    def test_nonexistent_document(self, granola_data: GranolaData):
        doc = granola_data.get_document("nonexistent")
        assert doc is None

    def test_document_without_transcript(self, granola_data: GranolaData):
        doc = granola_data.get_document("doc-002")
        assert doc is not None
        assert doc["has_transcript"] is False
        assert doc["transcript_segments"] == 0

    def test_document_with_null_updated_at(self, granola_data: GranolaData):
        doc = granola_data.get_document("doc-003")
        assert doc is not None
        assert doc["updated_at"] is None


class TestListDocuments:
    def test_list_all(self, granola_data: GranolaData):
        total, items = granola_data.list_documents()
        assert total == 5
        assert len(items) == 5

    def test_pagination(self, granola_data: GranolaData):
        total, items = granola_data.list_documents(limit=2, offset=0)
        assert total == 5
        assert len(items) == 2

    def test_pagination_offset(self, granola_data: GranolaData):
        _, first_page = granola_data.list_documents(limit=2, offset=0)
        _, second_page = granola_data.list_documents(limit=2, offset=2)
        first_ids = {item["id"] for item in first_page}
        second_ids = {item["id"] for item in second_page}
        assert first_ids.isdisjoint(second_ids)

    def test_sort_date_desc(self, granola_data: GranolaData):
        _, items = granola_data.list_documents(sort="date_desc")
        dates = [item["date"] for item in items]
        assert dates == sorted(dates, reverse=True)

    def test_sort_date_asc(self, granola_data: GranolaData):
        _, items = granola_data.list_documents(sort="date_asc")
        dates = [item["date"] for item in items]
        assert dates == sorted(dates)

    def test_sort_title(self, granola_data: GranolaData):
        _, items = granola_data.list_documents(sort="title")
        titles = [item["title"].lower() for item in items]
        assert titles == sorted(titles)

    def test_filter_by_date_from(self, granola_data: GranolaData):
        total, items = granola_data.list_documents(date_from="2025-02-01")
        for item in items:
            assert item["date"] >= "2025-02-01"
        assert total < 5

    def test_filter_by_attendee(self, granola_data: GranolaData):
        total, items = granola_data.list_documents(attendee="bob")
        assert total >= 1
        for item in items:
            doc = granola_data.get_document(item["id"])
            assert doc is not None
            emails = [a["email"] for a in doc["attendees"]]
            names = [a["name"].lower() for a in doc["attendees"]]
            assert any("bob" in n for n in names) or any("bob" in e for e in emails)


class TestSearchByPerson:
    def test_search_by_name(self, granola_data: GranolaData):
        results = granola_data.search_by_person("Alice")
        assert len(results) >= 3  # Alice is in most meetings

    def test_search_by_email(self, granola_data: GranolaData):
        results = granola_data.search_by_person("carol@example.com")
        assert len(results) >= 1

    def test_case_insensitive(self, granola_data: GranolaData):
        upper = granola_data.search_by_person("ALICE")
        lower = granola_data.search_by_person("alice")
        assert len(upper) == len(lower)

    def test_no_matches(self, granola_data: GranolaData):
        results = granola_data.search_by_person("nonexistent@nowhere.com")
        assert results == []

    def test_results_sorted_by_date_desc(self, granola_data: GranolaData):
        results = granola_data.search_by_person("Alice")
        dates = [r["date"] for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_limit(self, granola_data: GranolaData):
        results = granola_data.search_by_person("Alice", limit=1)
        assert len(results) <= 1


class TestGetTranscript:
    def test_with_transcript(self, granola_data: GranolaData):
        result = granola_data.get_transcript("doc-001")
        assert result is not None
        assert result["meeting_title"] == "Q1 Planning Session"
        assert result["total_segments"] == 3
        assert len(result["segments"]) == 3

    def test_segment_fields(self, granola_data: GranolaData):
        result = granola_data.get_transcript("doc-001")
        assert result is not None
        seg = result["segments"][0]
        assert "text" in seg
        assert "start_time" in seg
        assert "end_time" in seg
        assert "source" in seg

    def test_without_transcript(self, granola_data: GranolaData):
        result = granola_data.get_transcript("doc-002")
        assert result is not None
        assert result["segments"] == []
        assert result["total_segments"] == 0

    def test_nonexistent_document(self, granola_data: GranolaData):
        result = granola_data.get_transcript("nonexistent")
        assert result is None

    def test_format_passed_through(self, granola_data: GranolaData):
        result = granola_data.get_transcript("doc-001", format="timestamped")
        assert result is not None
        assert result["format"] == "timestamped"


class TestGetStats:
    def test_stats(self, granola_data: GranolaData):
        stats = granola_data.get_stats()
        assert stats["total_documents"] == 5
        assert stats["documents_with_transcripts"] == 2
        assert stats["date_range_start"] == "2025-01-15"
        assert stats["date_range_end"] == "2025-02-15"
        assert stats["unique_attendees"] >= 4

    def test_stats_total_transcripts(self, granola_data: GranolaData):
        stats = granola_data.get_stats()
        assert stats["total_transcripts"] == 2
