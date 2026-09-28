import hashlib
import re
from abc import ABC, abstractmethod
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.ingestion.parser import IbnBazFatwaParser, clean_text, normalize_arabic_for_retrieval
from app.models.domain import (
    FatwaDocument,
    QuestionAnswerPair,
    SourceCollection,
    SourceReference,
)


DORAR_URL_RE = re.compile(r"^https?://(?:www\.)?dorar\.net/feqhia/(\d+)(?:/[^?#]*)?/?$")
REFERENCE_RE = re.compile(
    r"\(\((?P<book>[^()]{2,120})\)\)(?:[^()\n]{0,100})\((?P<volume>\d+)\s*/\s*(?P<page>[\d\s،,\-–]+)\)"
)
MADHHABS = ("الحنفية", "المالكية", "الشافعية", "الحنابلة", "الظاهرية")


class SourceAdapter(ABC):
    collection: SourceCollection

    @abstractmethod
    def parse(self, html: str, url: str) -> FatwaDocument: ...


class IbnBazSourceAdapter(SourceAdapter):
    collection = SourceCollection.BINBAZ_REFERENCE

    def __init__(self) -> None:
        self._parser = IbnBazFatwaParser()

    def parse(self, html: str, url: str) -> FatwaDocument:
        return self._parser.parse(html, url)


class HackathonApprovedSourceAdapter(SourceAdapter):
    """Deterministic adapter for the approved Dorar Fiqh Encyclopedia.

    The adapter preserves the page hierarchy and explicit citations. It never
    assigns a scholar, madhhab, book, volume, page, or category unless that
    information is present in the page itself.
    """

    collection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE
    collection_name = "الموسوعة الفقهية – الدرر السنية"
    authority = "مؤسسة الدرر السنية"

    def parse(self, html: str, url: str) -> FatwaDocument:
        soup = BeautifulSoup(html, "html.parser")
        canonical_tag = soup.select_one('link[rel="canonical"]')
        canonical_hint = str(canonical_tag.get("href")) if canonical_tag and canonical_tag.get("href") else None
        external_id, canonical_url = self._canonical_url(canonical_hint or url)

        root = soup.select_one(".cntnt, main article, article, main")
        if not root:
            raise ValueError("Missing Dorar fiqh content root")
        title_node = root.select_one("h1") or soup.select_one("h1")
        if not title_node:
            raise ValueError("Missing Dorar fiqh entry title")
        title = clean_text(title_node.get_text(" ", strip=True))

        hierarchy = self._hierarchy(soup, canonical_url)
        qa_pairs = self._qa_pairs(root)
        content = self._source_content(root, title)
        if not content:
            raise ValueError("Missing Dorar fiqh source content")

        references = self._references(content)
        scholars = self._scholars(root)
        madhhabs = [name for name in MADHHABS if name in content]
        evidence = self._evidence_sections(content)
        full_original = "\n\n".join([title, content])
        retrieval_parts = [title, *hierarchy, content, *(pair.question for pair in qa_pairs), *(pair.answer for pair in qa_pairs)]
        retrieval_text = normalize_arabic_for_retrieval("\n".join(retrieval_parts))

        book = next((item for item in hierarchy if re.match(r"^(?:كِ|ك)تاب", item)), None)
        category = book
        subcategory = next((item for item in hierarchy if item.startswith("الباب")), None)

        return FatwaDocument(
            external_id=external_id,
            title=title,
            question=None,
            answer=content,
            full_original_text=full_original,
            retrieval_text=retrieval_text,
            answer_segments=self._segments(content),
            qa_pairs=qa_pairs,
            category_path=hierarchy,
            category_urls=self._hierarchy_urls(soup, canonical_url),
            tags=[item for item in [category, subcategory, title] if item],
            source_collection=self.collection,
            source_collection_name=self.collection_name,
            source_authority=self.authority,
            source_author=None,
            scholar=scholars[0] if len(scholars) == 1 else None,
            scholars=scholars,
            madhhab=madhhabs[0] if len(madhhabs) == 1 else None,
            madhhabs=madhhabs,
            book=book,
            category=category,
            subcategory=subcategory,
            topic=title,
            evidence=evidence,
            original_reference=references,
            source_organization=self.authority,
            source_domain="dorar.net",
            source_url=url,
            canonical_url=canonical_url,
            source_type="fiqh_encyclopedia_entry",
            language="ar",
            original_metadata={
                "parser": "dorar-feqhia-v1",
                "canonical_hint": canonical_hint,
                "hierarchy_depth": len(hierarchy),
                "qa_pair_count": len(qa_pairs),
                "reference_count": len(references),
            },
            content_hash=hashlib.sha256(full_original.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _canonical_url(candidate: str) -> tuple[int, str]:
        candidate = candidate.split("?")[0].split("#")[0].rstrip("/").replace("http://", "https://")
        match = DORAR_URL_RE.match(candidate)
        if not match:
            raise ValueError(f"Not an allowed Dorar fiqh URL: {candidate}")
        return int(match.group(1)), candidate

    @staticmethod
    def _hierarchy(soup: BeautifulSoup, canonical_url: str) -> list[str]:
        items: list[str] = []
        for node in soup.select(".breadcrumb a[href], nav[aria-label*='breadcrumb'] a[href]"):
            href = urljoin(canonical_url, str(node.get("href", "")))
            text = clean_text(node.get_text(" ", strip=True))
            if text and text not in {"الرئيسة", "الموسوعة الفقهية"} and DORAR_URL_RE.match(href.split("?")[0].rstrip("/")):
                items.append(text)
        return list(dict.fromkeys(items))

    @staticmethod
    def _hierarchy_urls(soup: BeautifulSoup, canonical_url: str) -> list[str]:
        urls: list[str] = []
        for node in soup.select(".breadcrumb a[href], nav[aria-label*='breadcrumb'] a[href]"):
            href = urljoin(canonical_url, str(node.get("href", ""))).split("?")[0].split("#")[0].rstrip("/")
            if DORAR_URL_RE.match(href) and href not in urls:
                urls.append(href)
        return urls

    @staticmethod
    def _source_content(root: Tag, title: str) -> str:
        clone = BeautifulSoup(str(root), "html.parser")
        for node in clone.select("script, style, form, button, .breadcrumb, #more-titles, footer, nav"):
            node.decompose()
        raw = clean_text(clone.get_text("\n", strip=True))
        if raw.startswith(title):
            raw = clean_text(raw[len(title):])
        raw = re.split(r"\n?المادة في سؤال وجواب\n?", raw, maxsplit=1)[0]
        raw = re.split(r"\n?انظر أيضا:?\n?", raw, maxsplit=1)[0]
        return clean_text(raw)

    @staticmethod
    def _qa_pairs(root: Tag) -> list[QuestionAnswerPair]:
        qa_root = root.find(string=re.compile(r"المادة في سؤال وجواب"))
        container = (qa_root.find_parent("section") or qa_root.find_parent()) if qa_root else None
        if not container:
            return []
        pairs: list[QuestionAnswerPair] = []
        for item in container.find_all(["div", "li"], recursive=False):
            question_node = item.find(["h3", "h4", "strong"])
            answer_node = item.find("p")
            if question_node and answer_node:
                question = clean_text(question_node.get_text(" ", strip=True))
                answer = clean_text(answer_node.get_text(" ", strip=True))
                if question and answer:
                    pairs.append(QuestionAnswerPair(question=question, answer=answer, sequence=len(pairs)))
        if pairs:
            return pairs
        text = clean_text(container.get_text("\n", strip=True))
        parts = re.split(r"\n(?=\d+\n)", text)
        for part in parts:
            match = re.search(r"(?:^|\n)\d+\n(.+?)\n(.+)$", part, re.DOTALL)
            if match:
                question, answer = map(clean_text, match.groups())
                if question and answer:
                    pairs.append(QuestionAnswerPair(question=question, answer=answer, sequence=len(pairs)))
        return pairs

    @staticmethod
    def _references(content: str) -> list[SourceReference]:
        references: list[SourceReference] = []
        seen: set[str] = set()
        for match in REFERENCE_RE.finditer(content):
            raw = clean_text(match.group(0))
            if raw in seen:
                continue
            seen.add(raw)
            references.append(SourceReference(raw=raw, book=clean_text(match.group("book")), volume=match.group("volume"), page=clean_text(match.group("page"))))
        return references

    @staticmethod
    def _scholars(root: Tag) -> list[str]:
        scholars: list[str] = []
        for node in root.select('a[href*="/history/event/"]'):
            name = clean_text(node.get_text(" ", strip=True))
            if name and name not in scholars:
                scholars.append(name)
        return scholars

    @staticmethod
    def _evidence_sections(content: str) -> list[str]:
        labels = []
        for line in content.splitlines():
            value = clean_text(line).rstrip(":")
            if value in {"الأدلة", "الدليل من الإجماع", "الدليل من السنة", "من الكتاب", "من السنة", "من الإجماع", "من الآثار", "وجه الدلالة"} and value not in labels:
                labels.append(value)
        return labels

    @staticmethod
    def _segments(content: str) -> list[str]:
        return [clean_text(part) for part in re.split(r"\n{2,}|(?=القولُ?\s+(?:الأول|الثاني))", content) if clean_text(part)]


def adapter_for(collection: SourceCollection) -> SourceAdapter:
    if collection == SourceCollection.OFFICIAL_HACKATHON_REFERENCE:
        return HackathonApprovedSourceAdapter()
    if collection == SourceCollection.BINBAZ_REFERENCE:
        return IbnBazSourceAdapter()
    raise ValueError(f"No source adapter configured for {collection}")
