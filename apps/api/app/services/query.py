import re
from app.models.domain import QueryAnalysis


class QueryUnderstandingService:
    async def analyze(self, query: str, language_hint: str | None = None) -> QueryAnalysis:
        language = language_hint or ("ar" if re.search(r"[\u0600-\u06ff]", query) else "en")
        normalized = query.casefold()
        category = "الصلاة" if any(term in normalized for term in ("صلاة", "أقصر", "prayer")) else None
        entities: dict[str, object] = {}
        duration = re.search(r"(\d+|[٠-٩]+|يوم|يومان|ثلاثة|ثلاث|أربعة|أربع|خمسة|خمس|ستة|ست|سبعة|سبع|ثمانية|ثمان|تسعة|تسع|عشرة|عشر)\s*(?:أيام|ايام|يومًا|يوما|days?)", query, re.I)
        if duration:
            number_words = {
                "يوم": 1, "يومان": 2, "ثلاثة": 3, "ثلاث": 3, "أربعة": 4, "أربع": 4,
                "خمسة": 5, "خمس": 5, "ستة": 6, "ست": 6, "سبعة": 7, "سبع": 7,
                "ثمانية": 8, "ثمان": 8, "تسعة": 9, "تسع": 9, "عشرة": 10, "عشر": 10,
            }
            raw_duration = duration.group(1)
            entities["duration_days"] = number_words.get(raw_duration, raw_duration)
        travel = any(term in normalized for term in ("مسافر", "سفر", "travel"))
        if travel:
            entities["travel"] = True
        missing: list[str] = []
        if travel and "duration_days" not in entities:
            missing.append("duration_days")
        complexity = []
        if any(term in normalized for term in ("طلاق", "ميراث", "court", "custody")) and len(query) > 250:
            complexity.append("personal_high_context_case")
        return QueryAnalysis(category=category, topic="صلاة المسافر" if travel else None, entities=entities, language=language, needs_clarification=bool(missing), missing_facts=missing, complexity_flags=complexity)
