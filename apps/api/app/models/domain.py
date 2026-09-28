from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, model_validator


SOURCE_AUTHOR = "الشيخ عبدالعزيز بن عبدالله بن باز"
SOURCE_DOMAIN = "binbaz.org.sa"


class SourceCollection(StrEnum):
    OFFICIAL_HACKATHON_REFERENCE = "OFFICIAL_HACKATHON_REFERENCE"
    BINBAZ_REFERENCE = "BINBAZ_REFERENCE"
    FUTURE_REFERENCE = "FUTURE_REFERENCE"


class DialogueTurn(BaseModel):
    speaker: str
    text: str
    sequence: int


class QuestionAnswerPair(BaseModel):
    question: str
    answer: str
    sequence: int


class SourceReference(BaseModel):
    raw: str
    book: str | None = None
    volume: str | None = None
    page: str | None = None


class FatwaDocument(BaseModel):
    external_id: int
    title: str
    question: str | None = None
    answer: str
    full_original_text: str
    retrieval_text: str
    answer_segments: list[str] = Field(default_factory=list)
    follow_up_dialogue: list[DialogueTurn] = Field(default_factory=list)
    qa_pairs: list[QuestionAnswerPair] = Field(default_factory=list)
    category_path: list[str] = Field(default_factory=list)
    category_urls: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE
    source_collection_name: str = "الموسوعة الفقهية – الدرر السنية"
    source_authority: str | None = "مؤسسة الدرر السنية"
    source_author: str | None = None
    scholar: str | None = None
    scholars: list[str] = Field(default_factory=list)
    madhhab: str | None = None
    madhhabs: list[str] = Field(default_factory=list)
    book: str | None = None
    volume: str | None = None
    page: str | None = None
    fatwa_number: str | None = None
    category: str | None = None
    subcategory: str | None = None
    topic: str | None = None
    evidence: list[str] = Field(default_factory=list)
    original_reference: list[SourceReference] = Field(default_factory=list)
    source_organization: str = "مؤسسة الدرر السنية"
    source_domain: str = "dorar.net"
    source_url: str
    canonical_url: str
    source_type: Literal["fatwa", "fiqh_encyclopedia_entry"] = "fiqh_encyclopedia_entry"
    language: Literal["ar"] = "ar"
    audio_url: str | None = None
    has_audio: bool = False
    original_metadata: dict[str, Any] = Field(default_factory=dict)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str

    @model_validator(mode="after")
    def validate_source(self) -> "FatwaDocument":
        if not self.answer.strip():
            raise ValueError("A source document requires non-empty source content")
        if self.source_collection == SourceCollection.BINBAZ_REFERENCE:
            if self.source_domain != "binbaz.org.sa" or "/fatwas/" not in self.canonical_url:
                raise ValueError("BINBAZ_REFERENCE requires a canonical binbaz.org.sa fatwa URL")
        if self.source_collection == SourceCollection.OFFICIAL_HACKATHON_REFERENCE:
            if self.source_domain != "dorar.net" or "/feqhia/" not in self.canonical_url:
                raise ValueError("OFFICIAL_HACKATHON_REFERENCE requires a canonical dorar.net/feqhia URL")
        return self


class FatwaChunk(BaseModel):
    fatwa_id: int
    title: str
    content: str
    category_path: list[str]
    source_url: str
    chunk_index: int
    source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE
    source_author: str | None = None
    source_authority: str | None = "مؤسسة الدرر السنية"


class EvidenceState(StrEnum):
    ANSWERABLE = "ANSWERABLE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    COMPLEX_CASE = "COMPLEX_CASE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class QueryAnalysis(BaseModel):
    intent: str = "fatwa_question"
    category: str | None = None
    topic: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    language: str = "ar"
    needs_clarification: bool = False
    missing_facts: list[str] = Field(default_factory=list)
    complexity_flags: list[str] = Field(default_factory=list)


class RetrievedEvidence(BaseModel):
    fatwa_id: int
    title: str
    excerpt: str
    source_url: str
    retrieval_score: float = Field(ge=0, le=1)
    reranker_score: float = Field(ge=0, le=1)
    coverage: float = Field(ge=0, le=1)
    category_path: list[str] = Field(default_factory=list)
    source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE
    source_collection_name: str = "الموسوعة الفقهية – الدرر السنية"
    source_authority: str | None = None
    scholar: str | None = None
    madhhabs: list[str] = Field(default_factory=list)
    original_reference: list[SourceReference] = Field(default_factory=list)
    source_type: str = "fiqh_encyclopedia_entry"
    conflicting_positions: bool = False


class EvidenceDecision(BaseModel):
    state: EvidenceState
    reasons: list[str]
    clarification_question: str | None = None


class Citation(BaseModel):
    fatwa_id: int
    title: str
    source_url: HttpUrl
    excerpt: str | None = None
    source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE
    source_collection_name: str = "الموسوعة الفقهية – الدرر السنية"
    source_authority: str | None = None
    scholar: str | None = None
    madhhabs: list[str] = Field(default_factory=list)
    original_reference: list[SourceReference] = Field(default_factory=list)
    source_type: str = "fiqh_encyclopedia_entry"


class AnswerResponse(BaseModel):
    state: EvidenceState
    language: str
    summary: str | None = None
    explanation: str | None = None
    clarification_question: str | None = None
    escalation_message: str | None = None
    citations: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def no_answer_without_source(self) -> "AnswerResponse":
        if self.state == EvidenceState.ANSWERABLE and (not self.summary or not self.citations):
            raise ValueError("ANSWERABLE responses require a summary and at least one valid source")
        return self


class AskRequest(BaseModel):
    query: str = Field(min_length=3, max_length=4000)
    language: str | None = None
    answer_mode: Literal["text", "voice", "both"] = "text"
    source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE


class AuthorityContact(BaseModel):
    name: str
    phone: str | None = None
    website: HttpUrl | None = None
    country: str
    is_verified: bool = False
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def verified_timestamp(self) -> "AuthorityContact":
        if self.is_verified and self.verified_at is None:
            raise ValueError("Verified contacts require verified_at")
        return self
