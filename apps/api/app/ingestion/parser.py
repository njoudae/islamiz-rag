import hashlib
import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from app.models.domain import DialogueTurn, FatwaDocument, SOURCE_AUTHOR, SourceCollection


FATWA_URL_RE = re.compile(r"^https?://(?:www\.)?binbaz\.org\.sa/fatwas/(\d+)(?:/[^?#]*)?$")
CATEGORY_URL_RE = re.compile(r"^https?://(?:www\.)?binbaz\.org\.sa/categories/(fiqhi|topic)/(\d+)(?:/fatwa)?/?$")
SPEAKER_RE = re.compile(r"^(المقدم|الشيخ|السائل|السائلة|س|ج)\s*[:：)]\s*(.*)$", re.DOTALL)


def clean_text(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\u200f", "").replace("\u200e", "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def normalize_arabic_for_retrieval(value: str) -> str:
    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي"}))
    value = re.sub(r"[^\w\s/]", " ", value).replace("ـ", " ")
    return re.sub(r"\s+", " ", value).strip()


def canonical_fatwa_url(url: str, html_canonical: str | None = None) -> tuple[int, str]:
    candidate = html_canonical or url
    candidate = candidate.split("?")[0].split("#")[0].rstrip("/")
    match = FATWA_URL_RE.match(candidate)
    if not match:
        raise ValueError(f"Not an allowed fatwa URL: {candidate}")
    return int(match.group(1)), candidate.replace("http://", "https://")


class IbnBazFatwaParser:
    """Deterministic adapter for canonical binbaz.org.sa fatwa pages."""

    def parse(self, html: str, url: str) -> FatwaDocument:
        soup = BeautifulSoup(html, "html.parser")
        canonical_tag = soup.select_one('link[rel="canonical"]')
        canonical_hint = canonical_tag.get("href") if canonical_tag else None
        external_id, canonical_url = canonical_fatwa_url(url, canonical_hint)
        title_node = soup.select_one("main h1, article h1, h1")
        if not title_node:
            raise ValueError("Missing fatwa title")
        title = clean_text(title_node.get_text(" ", strip=True))

        root = self._content_root(soup, title_node)
        question = self._section_after_label(root, ("السؤال", "س"), stop=("الجواب", "ج"))
        answer = self._section_after_label(root, ("الجواب", "ج"), stop=("الإبلاغ عن خطأ", "فتاوى ذات صلة"))
        if not answer:
            raise ValueError("Missing fatwa answer")

        dialogue = self._dialogue(answer)
        audio = self._audio_url(root, canonical_url)
        category_nodes = root.select('a[href*="/categories/"]')
        categories: list[str] = []
        category_urls: list[str] = []
        for node in category_nodes:
            href = urljoin(canonical_url, str(node.get("href", "")))
            if CATEGORY_URL_RE.match(href.split("?")[0].rstrip("/")):
                name = clean_text(node.get_text(" ", strip=True))
                if name and name not in categories:
                    categories.append(name)
                    category_urls.append(href)

        cleaned_answer = clean_text(answer)
        original_parts = [title]
        if question:
            original_parts.extend(["السؤال:", clean_text(question)])
        original_parts.extend(["الجواب:", cleaned_answer])
        full_original = "\n\n".join(original_parts)
        retrieval_parts = [title, clean_text(question or ""), cleaned_answer, " / ".join(categories)]
        retrieval_text = normalize_arabic_for_retrieval("\n".join(part for part in retrieval_parts if part))
        content_hash = hashlib.sha256(full_original.encode("utf-8")).hexdigest()

        return FatwaDocument(
            external_id=external_id,
            title=title,
            question=clean_text(question) if question else None,
            answer=cleaned_answer,
            full_original_text=full_original,
            retrieval_text=retrieval_text,
            answer_segments=self._answer_segments(cleaned_answer),
            follow_up_dialogue=dialogue,
            category_path=categories,
            category_urls=category_urls,
            tags=categories,
            source_collection=SourceCollection.BINBAZ_REFERENCE,
            source_collection_name="فتاوى الشيخ عبدالعزيز بن باز",
            source_authority="الموقع الرسمي لسماحة الشيخ ابن باز",
            source_author=SOURCE_AUTHOR,
            source_organization="الموقع الرسمي لسماحة الشيخ ابن باز",
            source_domain="binbaz.org.sa",
            source_url=url,
            canonical_url=canonical_url,
            source_type="fatwa",
            audio_url=audio,
            has_audio=bool(audio),
            original_metadata={"parser": "ibnbaz-v1", "canonical_hint": canonical_hint, "source_author": SOURCE_AUTHOR},
            content_hash=content_hash,
        )

    @staticmethod
    def _content_root(soup: BeautifulSoup, title_node: Tag) -> Tag:
        return title_node.find_parent("article") or title_node.find_parent("main") or soup.body or soup

    def _section_after_label(self, root: Tag, labels: tuple[str, ...], stop: tuple[str, ...]) -> str | None:
        nodes = list(root.find_all(["h2", "h3", "h4", "p", "div"], recursive=True))
        start: Tag | None = None
        for node in nodes:
            own = clean_text(node.get_text(" ", strip=True)).rstrip(":")
            if own in labels:
                start = node
                break
        if start is None:
            # Some pages put the label and content in one text node.
            raw = clean_text(root.get_text("\n", strip=True))
            pattern = rf"(?:{'|'.join(map(re.escape, labels))})\s*[:：]\s*(.+?)(?=(?:{'|'.join(map(re.escape, stop))})\s*[:：]|$)"
            match = re.search(pattern, raw, re.DOTALL)
            return clean_text(match.group(1)) if match else None
        collected: list[str] = []
        for sibling in start.find_all_next():
            if sibling is start or not isinstance(sibling, Tag):
                continue
            text = clean_text(sibling.get_text(" ", strip=True))
            if not text or sibling.find_parent(["nav", "footer"]):
                continue
            own = text.rstrip(":")
            if any(own == marker or own.startswith(f"{marker}:") for marker in stop):
                break
            if sibling.name in {"p", "h2", "h3", "h4"} and text not in collected:
                collected.append(text)
        return clean_text("\n\n".join(collected)) or None

    @staticmethod
    def _audio_url(root: Tag, base_url: str) -> str | None:
        node = root.select_one('audio source[src], audio[src], a[href*="files.zadapps.info"]')
        if not node:
            return None
        value = node.get("src") or node.get("href")
        return urljoin(base_url, str(value)) if value else None

    @staticmethod
    def _dialogue(answer: str) -> list[DialogueTurn]:
        turns: list[DialogueTurn] = []
        for paragraph in re.split(r"\n+", answer):
            match = SPEAKER_RE.match(paragraph.strip())
            if match and match.group(2).strip():
                turns.append(DialogueTurn(speaker=match.group(1), text=clean_text(match.group(2)), sequence=len(turns)))
        return turns

    @staticmethod
    def _answer_segments(answer: str) -> list[str]:
        return [clean_text(part) for part in re.split(r"\n{2,}", answer) if clean_text(part)]


def extract_fatwa_links(html: str, base_url: str) -> dict[int, str]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[int, str] = {}
    for node in soup.select("a[href]"):
        url = urljoin(base_url, str(node.get("href"))).split("?")[0].split("#")[0].rstrip("/")
        match = FATWA_URL_RE.match(url)
        if match:
            found.setdefault(int(match.group(1)), url)
    return found


def extract_category_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for node in soup.select("a[href]"):
        url = urljoin(base_url, str(node.get("href"))).split("?")[0].split("#")[0].rstrip("/")
        match = CATEGORY_URL_RE.match(url)
        if match:
            fatwa_view = f"{url}/fatwa" if not url.endswith("/fatwa") else url
            if fatwa_view not in links:
                links.append(fatwa_view)
    return links
