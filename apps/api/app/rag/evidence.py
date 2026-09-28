from app.models.domain import EvidenceDecision, EvidenceState, QueryAnalysis, RetrievedEvidence


HIGH_CONTEXT = {"طلاق", "الطلاق", "ميراث", "الفرائض", "تكفير", "نوازل", "قضاء"}


class EvidenceSufficiencyEvaluator:
    """Multi-signal safety gate; no single vector threshold decides an answer."""

    def decide(self, analysis: QueryAnalysis, evidence: list[RetrievedEvidence]) -> EvidenceDecision:
        if analysis.intent != "fatwa_question":
            return EvidenceDecision(state=EvidenceState.OUT_OF_SCOPE, reasons=["query is outside fatwa retrieval scope"])
        if analysis.complexity_flags or (analysis.category in HIGH_CONTEXT and analysis.missing_facts):
            return EvidenceDecision(state=EvidenceState.COMPLEX_CASE, reasons=["high-context case requires a qualified scholar"])
        if analysis.needs_clarification or analysis.missing_facts:
            question = self._grounded_clarification(analysis, evidence)
            return EvidenceDecision(state=EvidenceState.NEEDS_CLARIFICATION, reasons=["material circumstance is missing"], clarification_question=question)
        if not evidence:
            return EvidenceDecision(state=EvidenceState.INSUFFICIENT_EVIDENCE, reasons=["no source was retrieved"])

        direct = [item for item in evidence if item.coverage >= 0.72 and item.reranker_score >= 0.68]
        if not direct:
            return EvidenceDecision(state=EvidenceState.INSUFFICIENT_EVIDENCE, reasons=["sources do not directly cover the user circumstances"])

        top = direct[:3]
        if any(item.conflicting_positions for item in top):
            return EvidenceDecision(state=EvidenceState.CONFLICTING_EVIDENCE, reasons=["the approved source presents materially different positions"])
        spread = max(item.reranker_score for item in top) - min(item.reranker_score for item in top)
        if len(top) > 1 and spread > 0.28:
            return EvidenceDecision(state=EvidenceState.CONFLICTING_EVIDENCE, reasons=["retrieved evidence lacks stable agreement"])
        return EvidenceDecision(state=EvidenceState.ANSWERABLE, reasons=["direct source coverage", "strong reranker score", "source agreement"])

    @staticmethod
    def _grounded_clarification(analysis: QueryAnalysis, evidence: list[RetrievedEvidence]) -> str:
        missing = analysis.missing_facts[0] if analysis.missing_facts else "التفاصيل المؤثرة"
        known = {
            "duration_days": "كم تنوي الإقامة في وجهتك؟",
            "contract_status": "هل تم عقد النكاح أم لا؟",
            "time_relative_to_fajr": "هل وقع ذلك قبل الفجر أم بعده؟",
        }
        return known.get(missing, f"ما {missing} في حالتك؟")
