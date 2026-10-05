from abc import ABC, abstractmethod
from app.models.domain import AuthorityContact, RetrievedEvidence, SourceCollection, SourceReference


class FatwaRepository(ABC):
    @abstractmethod
    async def hybrid_search(self, query: str, language: str, category: str | None = None, limit: int = 10, source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE) -> list[RetrievedEvidence]: ...


class ContactRepository(ABC):
    @abstractmethod
    async def verified_contacts(self, country: str | None = None) -> list[AuthorityContact]: ...


class DemoFatwaRepository(FatwaRepository):
    async def hybrid_search(self, query: str, language: str, category: str | None = None, limit: int = 10, source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE) -> list[RetrievedEvidence]:
        if source_collection != SourceCollection.OFFICIAL_HACKATHON_REFERENCE:
            return []
        normalized = query.casefold()
        if any(term in normalized for term in ("مسافر", "سفر", "أقصر", "قصر", "travel", "shorten", "prayer")):
            return [RetrievedEvidence(
                fatwa_id=1455,
                title="المطلب الثاني: عدم نية الإقامة في السفر",
                excerpt="تعرض المادة حكم من نوى الإقامة، وتعرض قولين رئيسيين في المدة التي تقطع حكم السفر مع أدلة كل قول وعزوه.",
                source_url="https://dorar.net/feqhia/1455/%D8%A7%D9%84%D9%85%D8%B7%D9%84%D8%A8-%D8%A7%D9%84%D8%AB%D8%A7%D9%86%D9%8A-%D8%B9%D8%AF%D9%85-%D9%86%D9%8A%D8%A9-%D8%A7%D9%84%D8%A5%D9%82%D8%A7%D9%85%D8%A9-%D9%81%D9%8A-%D8%A7%D9%84%D8%B3%D9%81%D8%B1",
                retrieval_score=0.91,
                reranker_score=0.94,
                coverage=0.9,
                category_path=["كِتابُ الصَّلاةِ", "صلاة المسافر", "شروط قصر الصلاة"],
                source_collection=SourceCollection.OFFICIAL_HACKATHON_REFERENCE,
                source_collection_name="الموسوعة الفقهية – الدرر السنية",
                source_authority="مؤسسة الدرر السنية",
                madhhabs=["المالكية", "الشافعية", "الحنابلة"],
                original_reference=[SourceReference(raw="((الاستذكار)) (2/242)", book="الاستذكار", volume="2", page="242")],
                source_type="fiqh_encyclopedia_entry",
            )]
        return []


class EmptyContactRepository(ContactRepository):
    async def verified_contacts(self, country: str | None = None) -> list[AuthorityContact]:
        return []
