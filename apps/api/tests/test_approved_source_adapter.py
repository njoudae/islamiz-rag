from pathlib import Path

from app.ingestion.adapters import HackathonApprovedSourceAdapter
from app.models.domain import SourceCollection


FIXTURES = Path(__file__).parent / "fixtures"


def parse_fixture(name: str, url: str):
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return HackathonApprovedSourceAdapter().parse(html, url)


def test_preserves_dorar_hierarchy_and_source_identity():
    document = parse_fixture("dorar_synthetic_03.html", "https://dorar.net/feqhia/900003/")
    assert document.source_collection == SourceCollection.OFFICIAL_HACKATHON_REFERENCE
    assert document.source_collection_name == "الموسوعة الفقهية – الدرر السنية"
    assert document.source_authority == "مؤسسة الدرر السنية"
    assert document.source_author is None
    assert document.book == "كِتابُ الاختبار"
    assert document.category_path[-1].startswith("المَبحثُ الثالث")
    assert document.source_type == "fiqh_encyclopedia_entry"


def test_extracts_only_explicit_madhhabs_scholars_references_and_qa():
    document = parse_fixture("dorar_synthetic_03.html", "https://dorar.net/feqhia/900003/")
    assert set(document.madhhabs) == {"المالكية", "الشافعية"}
    assert document.madhhab is None
    assert document.scholar is None
    assert document.scholars == ["العالِمُ الاختباريُّ الأوَّل", "العالِمُ الاختباريُّ الثاني"]
    assert any(reference.book == "الاستذكار الاختباري" and reference.volume == "2" for reference in document.original_reference)
    assert len(document.qa_pairs) == 2


def test_missing_document_level_metadata_stays_null():
    document = parse_fixture("dorar_synthetic_01.html", "https://dorar.net/feqhia/900001/")
    assert document.fatwa_number is None
    assert document.volume is None
    assert document.page is None
    assert document.scholar is None
    assert document.madhhab is None
