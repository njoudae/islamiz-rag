from app.ingestion.audit import build_audit
from app.rag.chunking import structure_aware_chunks
from app.models.domain import DialogueTurn, FatwaDocument


def document(**overrides):
    data = dict(external_id=1, title="عنوان", question=None, answer="جواب موثق", full_original_text="عنوان\n\nجواب موثق", retrieval_text="عنوان جواب موثق", source_url="https://dorar.net/feqhia/1/x", canonical_url="https://dorar.net/feqhia/1/x", content_hash="hash")
    data.update(overrides)
    return FatwaDocument(**data)


def test_short_fatwa_is_one_source_identified_chunk():
    chunks = structure_aware_chunks(document())
    assert len(chunks) == 1
    assert chunks[0].fatwa_id == 1
    assert chunks[0].source_url.endswith("/feqhia/1/x")


def test_dialogue_pairs_keep_source_identity():
    doc = document(follow_up_dialogue=[DialogueTurn(speaker="المقدم", text="سؤال تال", sequence=0), DialogueTurn(speaker="الشيخ", text="جواب تال", sequence=1)])
    chunks = structure_aware_chunks(doc)
    assert all(chunk.fatwa_id == doc.external_id for chunk in chunks)
    assert any("المقدم" in chunk.content for chunk in chunks)


def test_audit_counts_missing_questions_audio_and_duplicates():
    one = document()
    duplicate = document(has_audio=True, audio_url="https://files.zadapps.info/a.mp3")
    audit = build_audit([one, duplicate])
    assert audit["total_fatwas"] == 2
    assert audit["unique_fatwas"] == 1
    assert audit["duplicates"] == 1
    assert audit["fatwas_without_questions"] == 2
    assert audit["fatwas_with_audio"] == 1
