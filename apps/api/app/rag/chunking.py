from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ingestion.parser import clean_text, normalize_arabic_for_retrieval
from app.models.domain import FatwaChunk, FatwaDocument, QuestionAnswerPair


@dataclass
class _Issue:
    heading: str
    original_text: str
    section_type: str
    ruling: str
    evidence_types: list[str] = field(default_factory=list)
    evidence_parts: list[str] = field(default_factory=list)
    qa_pairs: list[QuestionAnswerPair] = field(default_factory=list)


def _heading_type(heading: str) -> str:
    normalized = normalize_arabic_for_retrieval(heading)
    if normalized.startswith("الفرع"):
        return "far"
    if normalized.startswith("القول"):
        return "position"
    if normalized.startswith("المسالة"):
        return "masala"
    if normalized.startswith("المطلب"):
        return "matlab"
    if normalized.startswith("المبحث"):
        return "mabhas"
    return "issue"


def _evidence_type(heading: str, text: str) -> str:
    normalized = normalize_arabic_for_retrieval(f"{heading} {text[:160]}")
    if "الكتاب" in normalized or "القران" in normalized:
        return "Quran"
    if "السنة" in normalized or "رواه" in normalized or "حديث" in normalized:
        return "Sunnah"
    if "الاجماع" in normalized or "اجمع" in normalized:
        return "Ijma"
    return "other"


def _split_at_headings(text: str, predicate) -> list[tuple[str, str]]:
    lines = text.splitlines()
    parts: list[tuple[str, str]] = []
    heading = ""
    current: list[str] = []
    for line in lines:
        if predicate(line):
            if current and clean_text("\n".join(current)):
                parts.append((heading, "\n".join(current).strip()))
            heading = clean_text(line)
            current = [line]
        else:
            current.append(line)
    if current and clean_text("\n".join(current)):
        parts.append((heading, "\n".join(current).strip()))
    return parts or [("", text)]


def _is_primary_heading(line: str) -> bool:
    normalized = normalize_arabic_for_retrieval(line)
    return len(normalized) <= 180 and normalized.startswith(("الفرع", "القول", "المسالة"))


def _is_evidence_heading(line: str) -> bool:
    normalized = normalize_arabic_for_retrieval(line)
    return (
        normalized in {"الادلة", "الدليل", "الدليل من الكتاب", "الدليل من القران", "الدليل من السنة", "الدليل من الاجماع", "الدليل من الاثار"}
        or normalized.startswith(("اولا من الكتاب", "اولا من القران", "اولا من السنة", "اولا من الاجماع", "اولا من الاثار"))
        or normalized.startswith(("ثانيا من الكتاب", "ثانيا من القران", "ثانيا من السنة", "ثانيا من الاجماع", "ثانيا من الاثار"))
        or normalized.startswith(("ثالثا من الكتاب", "ثالثا من القران", "ثالثا من السنة", "ثالثا من الاجماع", "ثالثا من الاثار"))
    )


def _parse_issues(document: FatwaDocument) -> list[_Issue]:
    pieces = _split_at_headings(document.answer, _is_primary_heading)
    issues: list[_Issue] = []
    for heading, original in pieces:
        if not original.strip():
            continue
        topic = heading or document.title
        evidence_pieces = _split_at_headings(original, _is_evidence_heading)
        ruling_parts: list[str] = []
        evidence_parts: list[str] = []
        evidence_types: list[str] = []
        in_evidence = False
        for evidence_heading, part in evidence_pieces:
            if evidence_heading:
                in_evidence = True
                if normalize_arabic_for_retrieval(part) == normalize_arabic_for_retrieval(evidence_heading):
                    continue
                evidence_parts.append(part)
                evidence_types.append(_evidence_type(evidence_heading, part))
            elif in_evidence:
                evidence_parts.append(part)
                evidence_types.append(_evidence_type("", part))
            else:
                ruling_parts.append(part)
        ruling = clean_text("\n\n".join(ruling_parts)) or topic
        issues.append(
            _Issue(
                heading=topic,
                original_text=original,
                section_type=_heading_type(topic),
                ruling=ruling,
                evidence_types=list(dict.fromkeys(evidence_types)),
                evidence_parts=evidence_parts,
            )
        )
    for turn in document.follow_up_dialogue:
        original = f"{turn.speaker}: {turn.text}"
        issues.append(
            _Issue(
                heading=original,
                original_text=original,
                section_type="dialogue",
                ruling=turn.text,
            )
        )
    return issues or [_Issue(document.title, document.answer, _heading_type(document.title), document.answer)]


def _assign_qa_pairs(issues: list[_Issue], qa_pairs: list[QuestionAnswerPair]) -> None:
    for pair in qa_pairs:
        query_terms = set(normalize_arabic_for_retrieval(f"{pair.question} {pair.answer}").split())
        best = max(
            issues,
            key=lambda issue: len(query_terms & set(normalize_arabic_for_retrieval(issue.original_text).split())),
        )
        best.qa_pairs.append(pair)


def _hierarchy(document: FatwaDocument, issue: _Issue) -> dict[str, object]:
    hierarchy: dict[str, object] = {"path": document.category_path}
    for item in document.category_path:
        normalized = normalize_arabic_for_retrieval(item)
        if normalized.startswith("كتاب"):
            hierarchy["kitab"] = item
        elif normalized.startswith("الباب"):
            hierarchy["bab"] = item
        elif normalized.startswith("الفصل"):
            hierarchy["fasl"] = item
        elif normalized.startswith("المبحث"):
            hierarchy["mabhas"] = item
    document_heading = normalize_arabic_for_retrieval(document.title)
    if document_heading.startswith("المطلب"):
        hierarchy["matlab"] = document.title
    elif document_heading.startswith("المبحث") and "mabhas" not in hierarchy:
        hierarchy["mabhas"] = document.title
    if issue.section_type == "far":
        hierarchy["far"] = issue.heading
    elif issue.section_type == "position":
        hierarchy["position"] = issue.heading
    elif issue.section_type == "masala":
        hierarchy["masala"] = issue.heading
    return hierarchy


def _retrieval_text(
    topic: str,
    hierarchy: dict[str, object],
    ruling: str,
    original_text: str,
    qa_pairs: list[QuestionAnswerPair],
) -> str:
    aliases = [f"سؤال بديل: {pair.question}" for pair in qa_pairs]
    path = hierarchy.get("path", [])
    ruling_context = ruling if len(ruling) <= 700 else f"{ruling[:700].rstrip()}…"
    parts = [topic, *(path if isinstance(path, list) else []), f"الحكم: {ruling_context}", original_text, *aliases]
    return normalize_arabic_for_retrieval("\n".join(part for part in parts if part))


def _split_long_evidence(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [part.strip() for part in re.split(r"\n{2,}|(?m)(?=^\d+[-–]\s*)", text) if part.strip()]
    if len(paragraphs) == 1:
        return [text]
    groups: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > max_chars:
            groups.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        groups.append(current)
    return groups


def _extract_wajh_al_dalala(texts: list[str]) -> list[str]:
    results: list[str] = []
    for text in texts:
        current: list[str] = []
        for line in text.splitlines():
            normalized = normalize_arabic_for_retrieval(line)
            is_wajh = normalized.startswith("وجه الدلالة")
            is_next_evidence = bool(re.match(r"^\d+\s*[-–]", normalized)) or _is_evidence_heading(line)
            if current and is_next_evidence and not is_wajh:
                results.append("\n".join(current))
                current = []
            if is_wajh:
                if current:
                    results.append("\n".join(current))
                current = [line]
            elif current:
                current.append(line)
        if current:
            results.append("\n".join(current))
    return results


def structure_aware_chunks(document: FatwaDocument, max_chars: int = 3200) -> list[FatwaChunk]:
    issues = _parse_issues(document)
    _assign_qa_pairs(issues, document.qa_pairs)
    chunks: list[FatwaChunk] = []
    for issue in issues:
        hierarchy = _hierarchy(document, issue)
        tags = list(dict.fromkeys([*document.category_path, document.title, issue.heading]))
        pieces: list[tuple[str, list[str], list[str]]]
        if len(issue.original_text) <= max_chars or not issue.evidence_parts:
            pieces = [(issue.original_text, issue.evidence_types, issue.evidence_parts)]
        else:
            pieces = []
            for evidence_index, evidence in enumerate(issue.evidence_parts):
                evidence_type = issue.evidence_types[min(evidence_index, len(issue.evidence_types) - 1)] if issue.evidence_types else "other"
                for child in _split_long_evidence(evidence, max_chars):
                    pieces.append((child, [evidence_type], [child]))
        for piece_index, (original_text, evidence_types, evidence) in enumerate(pieces):
            if not original_text.strip():
                continue
            linked_qa_pairs = issue.qa_pairs if piece_index == 0 else []
            retrieval_text = _retrieval_text(issue.heading, hierarchy, issue.ruling, original_text, linked_qa_pairs)
            chunks.append(
                FatwaChunk(
                    fatwa_id=document.external_id,
                    title=document.title,
                    content=original_text,
                    category_path=document.category_path,
                    source_url=document.canonical_url,
                    chunk_index=len(chunks),
                    topic=issue.heading,
                    tags=tags,
                    hierarchy=hierarchy,
                    section_type="evidence_child" if len(pieces) > 1 else issue.section_type,
                    ruling=issue.ruling,
                    evidence=evidence,
                    evidence_types=list(dict.fromkeys(evidence_types)),
                    wajh_al_dalala=_extract_wajh_al_dalala(evidence),
                    qa_pairs=linked_qa_pairs,
                    original_text=original_text,
                    retrieval_text=retrieval_text,
                    source_collection=document.source_collection,
                    source_author=document.source_author,
                    source_authority=document.source_authority,
                )
            )
    return chunks
