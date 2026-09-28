from pathlib import Path
from app.ingestion.parser import IbnBazFatwaParser, clean_text, extract_fatwa_links, normalize_arabic_for_retrieval


FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_explicit_question_answer_audio_and_source_identity():
    html = (FIXTURES / "fatwa_simple.html").read_text(encoding="utf-8")
    fatwa = IbnBazFatwaParser().parse(html, "https://binbaz.org.sa/fatwas/10736/anything")
    assert fatwa.external_id == 10736
    assert fatwa.question == "هل النية في القلب تكفي؟"
    assert "النية محلها القلب" in fatwa.answer
    assert fatwa.has_audio is True
    assert fatwa.category_path == ["العبادات"]
    assert fatwa.source_domain == "binbaz.org.sa"
    assert fatwa.content_hash


def test_preserves_follow_up_dialogue():
    html = (FIXTURES / "fatwa_dialogue.html").read_text(encoding="utf-8")
    fatwa = IbnBazFatwaParser().parse(html, "https://binbaz.org.sa/fatwas/16674/sample")
    assert [(turn.speaker, turn.sequence) for turn in fatwa.follow_up_dialogue] == [("المقدم", 0), ("الشيخ", 1)]


def test_deduplicates_links_by_external_id():
    html = '<a href="/fatwas/7/one">a</a><a href="https://binbaz.org.sa/fatwas/7/two">b</a><a href="/articles/7/no">no</a>'
    assert extract_fatwa_links(html, "https://binbaz.org.sa/categories/fiqhi/8/fatwa") == {7: "https://binbaz.org.sa/fatwas/7/one"}


def test_arabic_normalization_is_retrieval_only():
    original = "إِنَّ النِّيَّةَ في القَلْبِ"
    normalized = normalize_arabic_for_retrieval(original)
    assert original == "إِنَّ النِّيَّةَ في القَلْبِ"
    assert "ا" in normalized and "ِ" not in normalized

