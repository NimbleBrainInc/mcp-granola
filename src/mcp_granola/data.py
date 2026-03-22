"""Granola data loader with caching and search functionality."""

import json
import re
from pathlib import Path
from typing import Any, cast

GRANOLA_DIR = Path.home() / "Library/Application Support/Granola"
CACHE_VERSIONS = ["cache-v6.json", "cache-v5.json", "cache-v4.json", "cache-v3.json"]


def _find_cache_path() -> Path | None:
    """Find the newest available Granola cache file."""
    for filename in CACHE_VERSIONS:
        path = GRANOLA_DIR / filename
        if path.exists():
            return path
    return None


class GranolaData:
    """Singleton class for loading and caching Granola data."""

    _instance: "GranolaData | None" = None
    _data: dict[str, Any] | None = None
    _last_modified: float | None = None
    _search_cache: dict[str, dict[str, Any]] | None = None
    _cache_path: Path | None = None

    def __new__(cls) -> "GranolaData":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _needs_reload(self) -> bool:
        """Check if data needs to be reloaded."""
        if self._cache_path is None:
            return self._data is None
        if not self._cache_path.exists():
            return self._data is None
        current_mtime = self._cache_path.stat().st_mtime
        return self._data is None or current_mtime != self._last_modified

    def _load(self) -> dict[str, Any]:
        """Load data from file, refreshing if changed."""
        if self._needs_reload():
            self._cache_path = _find_cache_path()
            if self._cache_path is None:
                self._data = {"documents": {}, "transcripts": {}, "documentPanels": {}}
                return self._data

            with open(self._cache_path) as f:
                raw = json.load(f)
            cache = raw["cache"]
            if isinstance(cache, str):
                cache = json.loads(cache)
            self._data = cache["state"]
            self._last_modified = self._cache_path.stat().st_mtime
            self._search_cache = None  # Invalidate search cache
        return self._data or {}

    @property
    def documents(self) -> dict[str, Any]:
        """Get all documents."""
        return self._load().get("documents", {})

    @property
    def transcripts(self) -> dict[str, list[Any]]:
        """Get all transcripts."""
        return self._load().get("transcripts", {})

    @property
    def panels(self) -> dict[str, dict[str, Any]]:
        """Get all document panels."""
        return self._load().get("documentPanels", {})

    def _build_search_cache(self) -> dict[str, dict[str, Any]]:
        """Build search cache with pre-extracted text."""
        if self._search_cache is not None:
            return self._search_cache

        # Snapshot documents first — accessing self.documents triggers _load(),
        # which can set self._search_cache = None mid-build if the file changed.
        docs = self.documents
        cache: dict[str, dict[str, Any]] = {}
        for doc_id, doc in docs.items():
            searchable = self._get_searchable_text(doc)
            title = doc.get("title") or ""
            created_at = doc.get("created_at") or ""
            cache[doc_id] = {
                "text": searchable.lower(),
                "title": title,
                "date": created_at[:10] if created_at else "",
                "attendees": self._get_attendees(doc),
            }
        self._search_cache = cache
        return self._search_cache

    def _get_searchable_text(self, doc: dict[str, Any]) -> str:
        """Extract all searchable text from a document."""
        texts = []
        texts.append(doc.get("title") or "")
        notes_plain = doc.get("notes_plain") or ""
        if not notes_plain and doc.get("notes"):
            notes_plain = self._extract_prosemirror_text(doc["notes"])
        texts.append(notes_plain)
        texts.append(doc.get("notes_markdown") or "")
        if doc.get("summary"):
            texts.append(doc["summary"])
        if doc.get("overview"):
            texts.append(doc["overview"])
        return " ".join(texts)

    def _get_attendees(self, doc: dict[str, Any]) -> list[dict[str, str]]:
        """Extract attendees from a document."""
        attendees = []
        people = doc.get("people") or {}

        # Creator
        creator = people.get("creator", {})
        if creator and creator.get("email"):
            attendees.append(
                {"name": creator.get("name") or "", "email": creator.get("email") or ""}
            )

        # Attendees
        for att in people.get("attendees", []):
            if att and att.get("email"):
                attendees.append({"name": att.get("name") or "", "email": att.get("email") or ""})

        return attendees

    def _extract_snippet(self, text: str, query: str, context: int = 100) -> str:
        """Extract a snippet around the query match."""
        text_lower = text.lower()
        query_lower = query.lower()
        idx = text_lower.find(query_lower)
        if idx == -1:
            return text[:200] + "..." if len(text) > 200 else text

        start = max(0, idx - context)
        end = min(len(text), idx + len(query) + context)

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def search(
        self,
        query: str,
        limit: int = 10,
        date_from: str | None = None,
        date_to: str | None = None,
        attendee: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search documents by keyword."""
        cache = self._build_search_cache()
        query_lower = query.lower()
        query_terms = query_lower.split()
        results = []

        for doc_id, cached in cache.items():
            # Date filtering
            if date_from and cached["date"] < date_from:
                continue
            if date_to and cached["date"] > date_to:
                continue

            # Attendee filtering
            if attendee:
                attendee_lower = attendee.lower()
                attendee_match = any(
                    attendee_lower in a["name"].lower() or attendee_lower in a["email"].lower()
                    for a in cached["attendees"]
                )
                if not attendee_match:
                    continue

            # Score calculation
            score = 0.0
            text = cached["text"]
            title_lower = cached["title"].lower()

            # Title matches are worth more
            for term in query_terms:
                if term in title_lower:
                    score += 10.0
                if term in text:
                    score += 1.0
                    # Count occurrences
                    score += text.count(term) * 0.1

            if score > 0:
                doc = self.documents[doc_id]
                snippets = []
                notes = doc.get("notes_plain") or ""
                if not notes and doc.get("notes"):
                    notes = self._extract_prosemirror_text(doc["notes"])
                if query_lower in notes.lower():
                    snippets.append(self._extract_snippet(notes, query))

                results.append(
                    {
                        "id": doc_id,
                        "title": cached["title"],
                        "date": cached["date"],
                        "score": score,
                        "snippets": snippets[:2],
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Get a document by ID with related data."""
        doc = self.documents.get(doc_id)
        if not doc:
            return None

        transcript = self.transcripts.get(doc_id, [])
        panels_dict = self.panels.get(doc_id, {})

        # Extract panels
        panels = []
        for panel_id, panel in panels_dict.items():
            content = self._extract_panel_text(panel.get("content", {}))
            panels.append({"id": panel_id, "title": panel.get("title") or "", "content": content})

        notes_plain = doc.get("notes_plain") or ""
        if not notes_plain and doc.get("notes"):
            notes_plain = self._extract_prosemirror_text(doc["notes"])

        return {
            "id": doc_id,
            "title": doc.get("title") or "",
            "created_at": doc.get("created_at") or "",
            "updated_at": doc.get("updated_at"),
            "notes_markdown": doc.get("notes_markdown") or "",
            "notes_plain": notes_plain,
            "attendees": self._get_attendees(doc),
            "panels": panels,
            "panels_available": "documentPanels" in self._load(),
            "has_transcript": len(transcript) > 0,
            "transcript_segments": len(transcript),
        }

    def _extract_panel_text(self, content: dict[str, Any]) -> str:
        """Extract text from ProseMirror content."""
        return self._extract_prosemirror_text(content)

    def _extract_prosemirror_text(self, node: dict[str, Any]) -> str:
        """Recursively extract text from ProseMirror nodes."""
        if node.get("type") == "text":
            return node.get("text", "")

        texts = []
        for child in node.get("content", []):
            text = self._extract_prosemirror_text(child)
            if text:
                texts.append(text)

        node_type = node.get("type", "")
        if node_type in ("paragraph", "heading", "listItem"):
            return " ".join(texts) + "\n"
        if node_type == "bulletList":
            return "\n".join(f"- {t.strip()}" for t in texts if t.strip())

        return " ".join(texts)

    def list_documents(
        self,
        limit: int = 20,
        offset: int = 0,
        date_from: str | None = None,
        date_to: str | None = None,
        attendee: str | None = None,
        sort: str = "date_desc",
    ) -> tuple[int, list[dict[str, Any]]]:
        """List documents with filtering and pagination."""
        cache = self._build_search_cache()
        items = []

        for doc_id, cached in cache.items():
            # Date filtering
            if date_from and cached["date"] < date_from:
                continue
            if date_to and cached["date"] > date_to:
                continue

            # Attendee filtering
            if attendee:
                attendee_lower = attendee.lower()
                attendee_match = any(
                    attendee_lower in a["name"].lower() or attendee_lower in a["email"].lower()
                    for a in cached["attendees"]
                )
                if not attendee_match:
                    continue

            transcript = self.transcripts.get(doc_id, [])
            items.append(
                {
                    "id": doc_id,
                    "title": cached["title"],
                    "date": cached["date"],
                    "attendee_count": len(cached["attendees"]),
                    "has_transcript": len(transcript) > 0,
                }
            )

        # Sort
        if sort == "date_desc":
            items.sort(key=lambda x: x["date"], reverse=True)
        elif sort == "date_asc":
            items.sort(key=lambda x: x["date"])
        elif sort == "title":
            items.sort(key=lambda x: x["title"].lower())

        total = len(items)
        return total, items[offset : offset + limit]

    def search_by_person(
        self,
        person: str,
        limit: int = 20,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find meetings with a specific person."""
        cache = self._build_search_cache()
        person_lower = person.lower()
        results = []

        for doc_id, cached in cache.items():
            # Date filtering
            if date_from and cached["date"] < date_from:
                continue
            if date_to and cached["date"] > date_to:
                continue

            for att in cached["attendees"]:
                if person_lower in att["name"].lower() or person_lower in att["email"].lower():
                    transcript = self.transcripts.get(doc_id, [])
                    results.append(
                        {
                            "id": doc_id,
                            "title": cached["title"],
                            "date": cached["date"],
                            "attendee_count": len(cached["attendees"]),
                            "has_transcript": len(transcript) > 0,
                        }
                    )
                    break

        results.sort(key=lambda x: x["date"], reverse=True)
        return results[:limit]

    def get_transcript(self, doc_id: str, format: str = "text") -> dict[str, Any] | None:
        """Get transcript for a document."""
        doc = self.documents.get(doc_id)
        if not doc:
            return None

        transcript = self.transcripts.get(doc_id, [])

        segments = []
        for seg in transcript:
            segments.append(
                {
                    "text": seg.get("text", ""),
                    "start_time": seg.get("start_timestamp", ""),
                    "end_time": seg.get("end_timestamp", ""),
                    "source": seg.get("source", ""),
                }
            )

        return {
            "meeting_id": doc_id,
            "meeting_title": doc.get("title") or "",
            "segments": segments,
            "total_segments": len(segments),
            "format": format,
        }

    def get_meeting_summaries(
        self,
        date_from: str,
        date_to: str,
        person: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get meetings with notes in a date range, optionally filtered by person."""
        cache = self._build_search_cache()
        results = []

        for doc_id, cached in cache.items():
            if cached["date"] < date_from or cached["date"] > date_to:
                continue

            if person:
                person_lower = person.lower()
                if not any(
                    person_lower in a["name"].lower() or person_lower in a["email"].lower()
                    for a in cached["attendees"]
                ):
                    continue

            doc = self.get_document(doc_id)
            if not doc:
                continue

            results.append(
                {
                    "id": doc_id,
                    "title": doc["title"],
                    "date": cached["date"],
                    "notes_plain": doc["notes_plain"],
                    "attendees": doc["attendees"],
                }
            )

        results.sort(key=lambda x: x["date"], reverse=True)
        return results

    def extract_action_items(
        self,
        meeting_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        person: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract action items from meeting notes and panels.

        Can target a single meeting by ID, or multiple meetings by date range.
        """
        # Determine which meetings to process
        if meeting_id:
            doc = self.get_document(meeting_id)
            if not doc:
                return []
            cache = self._build_search_cache()
            cached = cache.get(meeting_id)
            meetings = [
                {
                    "id": meeting_id,
                    "title": doc["title"],
                    "date": cached["date"] if cached else "",
                    "doc": doc,
                }
            ]
        elif date_from and date_to:
            summaries = self.get_meeting_summaries(
                date_from=date_from, date_to=date_to, person=person
            )
            meetings = []
            for s in summaries:
                doc = self.get_document(s["id"])
                if doc:
                    meetings.append(
                        {
                            "id": s["id"],
                            "title": s["title"],
                            "date": s["date"],
                            "doc": doc,
                        }
                    )
        else:
            return []

        # Extract action items from each meeting
        items: list[dict[str, Any]] = []
        for m in meetings:
            doc = cast(dict[str, Any], m["doc"])

            # Extract from panels (highest quality — Granola's AI panels)
            panels: list[dict[str, Any]] = doc.get("panels", [])
            for panel in panels:
                if "action" in panel.get("title", "").lower():
                    for line in str(panel.get("content", "")).split("\n"):
                        line = line.strip().lstrip("- ").strip()
                        if line:
                            items.append(
                                {
                                    "action": line,
                                    "meeting_id": m["id"],
                                    "meeting_title": m["title"],
                                    "meeting_date": m["date"],
                                    "source": "panel",
                                }
                            )

            # Extract from notes — look for bullet points and action-oriented lines
            notes: str = doc.get("notes_plain", "") or ""
            for line in notes.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Match bullet points (-, *, [ ], [x])
                bullet_match = re.match(r"^[-*]\s+(.+)", line)
                checkbox_match = re.match(r"^\[[ x]]\s+(.+)", line, re.IGNORECASE)
                if bullet_match:
                    text = bullet_match.group(1).strip()
                    # Skip if already captured from panels
                    if not any(text in item["action"] or item["action"] in text for item in items):
                        items.append(
                            {
                                "action": text,
                                "meeting_id": m["id"],
                                "meeting_title": m["title"],
                                "meeting_date": m["date"],
                                "source": "notes",
                            }
                        )
                elif checkbox_match:
                    items.append(
                        {
                            "action": checkbox_match.group(1).strip(),
                            "meeting_id": m["id"],
                            "meeting_title": m["title"],
                            "meeting_date": m["date"],
                            "source": "notes",
                        }
                    )

        return items

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the data."""
        docs = self.documents
        transcripts = self.transcripts

        dates = [d.get("created_at", "")[:10] for d in docs.values() if d.get("created_at")]
        dates.sort()

        # Count unique attendees
        all_attendees: set[str] = set()
        cache = self._build_search_cache()
        for cached in cache.values():
            for att in cached["attendees"]:
                if att["email"]:
                    all_attendees.add(att["email"])

        docs_with_transcripts = sum(
            1 for doc_id in docs if doc_id in transcripts and transcripts[doc_id]
        )

        return {
            "total_documents": len(docs),
            "total_transcripts": len(transcripts),
            "documents_with_transcripts": docs_with_transcripts,
            "date_range_start": dates[0] if dates else "",
            "date_range_end": dates[-1] if dates else "",
            "unique_attendees": len(all_attendees),
        }


# Singleton instance
_data: GranolaData | None = None


def get_data() -> GranolaData:
    """Get the singleton GranolaData instance."""
    global _data
    if _data is None:
        _data = GranolaData()
    return _data
