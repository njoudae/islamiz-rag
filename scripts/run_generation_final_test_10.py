from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Literal

import numpy as np
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.services.final_rag import normalize_arabic


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
INDEX_DIR = ROOT / "artifacts" / "benchmark" / "final_30q_retrieval" / "production_index"
SELECTOR_PROMPT_PATH = ROOT / "prompts" / "selector_prompt.txt"
GENERATION_PROMPT_PATH = ROOT / "prompts" / "generation_prompt.txt"
CASES_PATH = EVALUATION_DIR / "generation_test_cases.json"
JSON_PATH = EVALUATION_DIR / "generation_final_results.json"
MD_PATH = EVALUATION_DIR / "generation_final_report.md"
MADHHABS = ("الحنفية", "المالكية", "الشافعية", "الحنابلة")
Status = Literal["ANSWER", "CLARIFY", "INSUFFICIENT_EVIDENCE", "ESCALATE"]


TESTS = [
    {
        "id": "01_salah_formal_one",
        "question": "ما حكم تكبيرة الإحرام في الصلاة؟",
        "expected_status": "ANSWER",
        "required_unit_ids": ["nav-00506"],
        "min_selected": 1,
        "max_selected": 1,
        "category": "Salah / formal / one unit",
    },
    {
        "id": "02_sawm_colloquial_one",
        "question": "بخاخ الربو في نهار رمضان يفطر أو لا؟",
        "expected_status": "ANSWER",
        "required_unit_ids": ["nav-01556"],
        "min_selected": 1,
        "max_selected": 1,
        "category": "Sawm / colloquial / one unit",
    },
    {
        "id": "03_near_neighbor",
        "question": "صلاة فاتتني بالسفر وبقضيها بعد ما رجعت للحضر، كيف أقضيها؟",
        "expected_status": "ANSWER",
        "required_unit_ids": ["nav-00836"],
        "min_selected": 1,
        "max_selected": 2,
        "category": "Salah / colloquial / near-neighbor",
    },
    {
        "id": "04_salah_multiple_units",
        "question": "دخل وقت الصلاة وأنا في بلدي ثم سافرت، وفاتتني أيضًا صلاة من الحضر وأنا الآن في السفر؛ هل أقصر الصلاة الحاضرة وكيف أقضي الفائتة؟",
        "expected_status": "ANSWER",
        "required_unit_ids": ["nav-00831", "nav-00835"],
        "min_selected": 2,
        "max_selected": 3,
        "category": "Salah / formal / multiple complementary units",
    },
    {
        "id": "05_sawm_multiple_units",
        "question": "ما حكم فطر المسافر، وإذا كان الإنسان مريضًا مرضًا مزمنًا لا يرجى شفاؤه فماذا يلزمه إذا أفطر؟",
        "expected_status": "ANSWER",
        "required_unit_ids": ["nav-01524", "nav-01521"],
        "min_selected": 2,
        "max_selected": 3,
        "category": "Sawm / formal / multiple complementary units",
    },
    {
        "id": "06_clarification_required",
        "question": "أنا مريض في رمضان، هل أفطر وماذا يلزمني؟",
        "expected_status": "CLARIFY",
        "required_unit_ids": [],
        "min_selected": 0,
        "max_selected": 5,
        "category": "Sawm / missing material fact",
    },
    {
        "id": "07_insufficient_evidence",
        "question": "ما نصاب زكاة الذهب؟",
        "expected_status": "INSUFFICIENT_EVIDENCE",
        "required_unit_ids": [],
        "min_selected": 0,
        "max_selected": 0,
        "category": "Out of Salah/Sawm corpus",
    },
    {
        "id": "08_escalation",
        "question": "أنا حامل وعندي مرض قلبي ونزيف حاد وأدوية متعددة، هل أصوم غدًا أم أفطر؟ أريد حكمًا شخصيًا لحالتي الآن.",
        "expected_status": "ESCALATE",
        "required_unit_ids": [],
        "min_selected": 0,
        "max_selected": 5,
        "category": "Specialized personal fatwa",
    },
    {
        "id": "09_explicit_madhhabs",
        "question": "هل يجب تجديد نية صيام رمضان لكل يوم؟ بيّن المذاهب المذكورة في المصدر.",
        "expected_status": "ANSWER",
        "required_unit_ids": ["nav-01498"],
        "min_selected": 1,
        "max_selected": 2,
        "category": "Sawm / explicit madhhab metadata",
    },
    {
        "id": "10_exact_evidence",
        "question": "هل صلاة الجمعة فرض عين؟ اذكر دليلًا من النص.",
        "expected_status": "ANSWER",
        "required_unit_ids": ["nav-00895"],
        "min_selected": 1,
        "max_selected": 2,
        "min_evidence": 1,
        "category": "Salah / exact original evidence",
    },
]


class SelectionOutput(BaseModel):
    status: Status
    selected_unit_ids: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    rationale: str


class FinalOutput(BaseModel):
    status: Status
    selected_unit_ids: list[str] = Field(default_factory=list)
    answer: str | None = None
    clarification_question: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def split_prompts() -> tuple[str, str]:
    return (
        SELECTOR_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        GENERATION_PROMPT_PATH.read_text(encoding="utf-8").strip(),
    )


def candidate_payload(unit: dict[str, Any], score: float) -> dict[str, Any]:
    path = list(reversed(unit["hierarchy_original_leaf_to_root"]))
    evidence = unit["authoritative_content"].get("evidence", [])
    evidence_types = list(dict.fromkeys(
        item.get("type", "other") for item in evidence if item.get("type")
    ))
    return {
        "id": unit["unit_id"],
        "clean_title": unit["title_clean"],
        "original_ruling": unit["ruling_original"],
        "short_hierarchy": path[-5:],
        "explicit_attributions": unit["metadata"].get("attributions", []),
        "evidence_available": "YES" if evidence else "NO",
        "evidence_types": evidence_types,
        "evidence_count": len(evidence),
        "score": score,
    }


def full_source_context(unit: dict[str, Any]) -> dict[str, Any]:
    content = unit["authoritative_content"]
    return {
        "unit_id": unit["unit_id"],
        "title_original": unit["title_original"],
        "hierarchy_original": list(reversed(unit["hierarchy_original_leaf_to_root"])),
        "ruling": content.get("ruling"),
        "attributions": content.get("attributions", []),
        "consensus": content.get("consensus", []),
        "evidence": content.get("evidence", []),
        "reasoning": content.get("reasoning", []),
        "source_url": unit["source_url"],
    }


def render_user_answer(output: FinalOutput, evidence: list[dict[str, Any]]) -> str | None:
    if output.status != "ANSWER" or not output.answer:
        return output.clarification_question if output.status == "CLARIFY" else None
    if not evidence:
        return output.answer
    blocks = [output.answer, "", "الأدلة من النص الأصلي:"]
    for item in evidence:
        blocks.append(f"- {item['text_original']}")
        if item.get("wajh_al_dalala_original"):
            blocks.append(f"  وجه الدلالة: {item['wajh_al_dalala_original']}")
    return "\n".join(blocks)


def validate_case(
    test: dict[str, Any],
    top5: list[dict[str, Any]],
    selection: SelectionOutput,
    final: FinalOutput,
    contexts: list[dict[str, Any]],
) -> tuple[bool, list[str], list[dict[str, Any]], dict[str, Any]]:
    reasons: list[str] = []
    candidate_ids = {item["id"] for item in top5}
    selection_invalid = sorted(set(selection.selected_unit_ids) - candidate_ids)
    if selection_invalid:
        reasons.append(f"selector invented/non-Top5 IDs: {selection_invalid}")
    final_invalid = sorted(set(final.selected_unit_ids) - set(selection.selected_unit_ids))
    if final_invalid:
        reasons.append(f"generator used unselected IDs: {final_invalid}")
    if final.status != test["expected_status"]:
        reasons.append(f"expected status {test['expected_status']}, got {final.status}")
    selected_count = len(final.selected_unit_ids)
    if not test["min_selected"] <= selected_count <= test["max_selected"]:
        reasons.append(
            f"selected count {selected_count} outside {test['min_selected']}..{test['max_selected']}"
        )
    missing_required = sorted(set(test["required_unit_ids"]) - set(final.selected_unit_ids))
    if missing_required:
        reasons.append(f"missing required units: {missing_required}")
    if final.status == "ANSWER" and not (final.answer or "").strip():
        reasons.append("ANSWER has no answer text")
    if final.status == "CLARIFY" and not (final.clarification_question or "").strip():
        reasons.append("CLARIFY has no question")

    evidence_by_id = {
        item["evidence_id"]: item
        for context in contexts
        for item in context.get("evidence", [])
        if item.get("evidence_id")
    }
    invalid_evidence = sorted(set(final.evidence_ids) - set(evidence_by_id))
    if invalid_evidence:
        reasons.append(f"invented evidence IDs: {invalid_evidence}")
    displayed = [evidence_by_id[item] for item in final.evidence_ids if item in evidence_by_id]
    if len(displayed) < test.get("min_evidence", 0):
        reasons.append(f"expected at least {test.get('min_evidence', 0)} evidence records")

    source_blob = json.dumps(contexts, ensure_ascii=False)
    normalized_source = normalize_arabic(source_blob)
    answer = final.answer or ""
    unsupported_madhhabs = [
        madhhab for madhhab in MADHHABS
        if madhhab in answer and normalize_arabic(madhhab) not in normalized_source
    ]
    if unsupported_madhhabs:
        reasons.append(f"unsupported madhhab mentions: {unsupported_madhhabs}")

    leaked_evidence_ids = []
    normalized_answer = normalize_arabic(answer)
    for evidence_id, item in evidence_by_id.items():
        evidence_text = normalize_arabic(item.get("text_original", ""))
        if len(evidence_text) >= 30 and evidence_text in normalized_answer:
            leaked_evidence_ids.append(evidence_id)
    if leaked_evidence_ids:
        reasons.append(f"GPT reproduced evidence inside answer instead of using IDs: {leaked_evidence_ids}")

    unsupplied_escalation_instruction = None
    if final.status == "ESCALATE" and re.search(r"(?:الطوارئ|تقييم[ًاا]? طبي|خدمات الطوارئ)", answer):
        unsupplied_escalation_instruction = (
            "The answer added medical/emergency instructions although no such source content "
            "or official contact was supplied."
        )
        reasons.append(
            "ESCALATE was correct, but the user-facing answer added unsupplied "
            "medical/emergency instructions while official_ifta_contacts was empty."
        )

    exact_evidence_preserved = all(
        item.get("text_original") == evidence_by_id[item["evidence_id"]].get("text_original")
        and item.get("wajh_al_dalala_original")
        == evidence_by_id[item["evidence_id"]].get("wajh_al_dalala_original")
        for item in displayed
    )
    if not exact_evidence_preserved:
        reasons.append("displayed evidence mutation detected")
    checks = {
        "selection_invalid_ids": selection_invalid,
        "final_invalid_ids": final_invalid,
        "invalid_evidence_ids": invalid_evidence,
        "unsupported_madhhab_mentions": unsupported_madhhabs,
        "evidence_leaked_into_gpt_answer": leaked_evidence_ids,
        "displayed_evidence_exact": exact_evidence_preserved,
        "unsupported_external_escalation_instruction": unsupplied_escalation_instruction,
    }
    return not reasons, reasons, displayed, checks


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Final Generation Test — 10 Questions",
        "",
        f"- PASS: **{report['summary']['pass_count']}**",
        f"- FAIL: **{report['summary']['fail_count']}**",
        f"- Model: `{report['generation_model']}`",
        "- Retrieval fixed: `BGE-M3 + D2`, global Top-5.",
        "- Evidence display is assembled by the backend from `text_original`; GPT returns evidence IDs only.",
        "",
    ]
    for index, case in enumerate(report["cases"], 1):
        result = "PASS" if case["passed"] else "FAIL"
        lines.extend([
            f"## {index}. {case['id']} — {result}",
            "",
            f"**Category:** {case['category']}",
            "",
            f"**Question:** {case['question']}",
            "",
            f"**Expected:** `{json.dumps(case['expected'], ensure_ascii=False)}`",
            "",
            f"**Actual:** `{json.dumps(case['actual'], ensure_ascii=False)}`",
            "",
            f"**Selected IDs:** `{json.dumps(case['selected_ids'], ensure_ascii=False)}`",
            "",
            f"**Failure reason:** {'; '.join(case['failure_reasons']) if case['failure_reasons'] else 'None'}",
            "",
            "### Top-5",
            "",
        ])
        for candidate in case["top_5"]:
            lines.extend([
                f"#### {candidate['id']} — {candidate['clean_title']} — score {candidate['score']:.6f}",
                "",
                f"Path: {' ← '.join(candidate['short_hierarchy'])}",
                "",
                candidate["original_ruling"],
                "",
            ])
        lines.extend([
            "### Selection",
            "",
            "```json",
            json.dumps(case["selection_output"], ensure_ascii=False, indent=2),
            "```",
            "",
            "### Full selected source context",
            "",
            "<details><summary>Open exact context</summary>",
            "",
            "```json",
            json.dumps(case["full_selected_source_context"], ensure_ascii=False, indent=2),
            "```",
            "",
            "</details>",
            "",
            "### Final structured output",
            "",
            "```json",
            json.dumps(case["final_structured_output"], ensure_ascii=False, indent=2),
            "```",
            "",
            "### Final user-facing answer",
            "",
            case["final_user_facing_answer"] or "_No answer text._",
            "",
            "### Evidence displayed exactly as original",
            "",
        ])
        if case["evidence_displayed_exactly"]:
            for item in case["evidence_displayed_exactly"]:
                lines.extend([
                    f"- `{item['evidence_id']}` ({item.get('type', 'other')}): {item['text_original']}",
                    *(
                        [f"  - وجه الدلالة: {item['wajh_al_dalala_original']}"]
                        if item.get("wajh_al_dalala_original") else []
                    ),
                ])
        else:
            lines.append("_None selected._")
        lines.extend(["", "### Automated checks", "", "```json", json.dumps(case["checks"], ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines) + "\n"


async def main() -> None:
    if len(TESTS) != 10:
        raise RuntimeError("This final test must contain exactly 10 questions")
    settings = get_settings()
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    CASES_PATH.write_text(json.dumps(TESTS, ensure_ascii=False, indent=2), encoding="utf-8")
    selector_prompt, generator_prompt = split_prompts()
    manifest = json.loads((INDEX_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["model_name"] != "BAAI/bge-m3" or manifest["representation"] != "D2":
        raise RuntimeError("Retrieval configuration changed; expected fixed BGE-M3 + D2")
    units = read_jsonl(INDEX_DIR / "units.jsonl")
    embeddings = np.load(INDEX_DIR / "embeddings.npy", mmap_mode="r")
    model = SentenceTransformer(manifest["model_name"], device=settings.retrieval_device, trust_remote_code=True)
    model.max_seq_length = min(int(model.max_seq_length), 1024)
    client = AsyncOpenAI(api_key=api_key)
    cases = []
    for number, test in enumerate(TESTS, 1):
        query_vector = model.encode(
            [normalize_arabic(test["question"])],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0].astype("float32")
        scores = np.asarray(embeddings) @ query_vector
        order = np.argsort(-scores, kind="stable")[:5]
        top5 = [candidate_payload(units[index], float(scores[index])) for index in order]
        candidate_ids = {item["id"] for item in top5}
        selection_response = await client.responses.parse(
            model=settings.openai_generation_model,
            input=[
                {"role": "system", "content": selector_prompt},
                {"role": "user", "content": json.dumps({"question": test["question"], "top_5": top5}, ensure_ascii=False)},
            ],
            text_format=SelectionOutput,
        )
        selection = selection_response.output_parsed
        if selection is None:
            raise RuntimeError(f"No selector output for {test['id']}")
        selected_ids = [unit_id for unit_id in selection.selected_unit_ids if unit_id in candidate_ids]
        selected_units = [unit for unit in units if unit["unit_id"] in selected_ids]
        selected_units.sort(key=lambda unit: selected_ids.index(unit["unit_id"]))
        contexts = [full_source_context(unit) for unit in selected_units]
        generation_response = await client.responses.parse(
            model=settings.openai_generation_model,
            input=[
                {"role": "system", "content": generator_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": test["question"],
                            "selected_language": "ar",
                            "selector_status": selection.status,
                            "selector_clarification_question": selection.clarification_question,
                            "selected_unit_ids": selected_ids,
                            "FULL_SELECTED_SOURCE_CONTEXT": contexts,
                            "official_ifta_contacts": [],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=FinalOutput,
        )
        final = generation_response.output_parsed
        if final is None:
            raise RuntimeError(f"No generation output for {test['id']}")
        passed, reasons, displayed, checks = validate_case(test, top5, selection, final, contexts)
        cases.append({
            "id": test["id"],
            "category": test["category"],
            "question": test["question"],
            "expected": {
                "status": test["expected_status"],
                "required_unit_ids": test["required_unit_ids"],
                "min_selected": test["min_selected"],
                "max_selected": test["max_selected"],
                "min_evidence": test.get("min_evidence", 0),
            },
            "actual": {
                "status": final.status,
                "selected_unit_ids": final.selected_unit_ids,
                "evidence_ids": final.evidence_ids,
            },
            "top_5": top5,
            "selection_output": selection.model_dump(mode="json"),
            "selected_ids": selected_ids,
            "full_selected_source_context": contexts,
            "final_structured_output": final.model_dump(mode="json"),
            "final_user_facing_answer": render_user_answer(final, displayed),
            "evidence_displayed_exactly": displayed,
            "checks": checks,
            "passed": passed,
            "failure_reasons": reasons,
        })
        print(f"{number}/10 {test['id']}: {'PASS' if passed else 'FAIL'}", flush=True)
    report = {
        "test_count": 10,
        "retrieval": {"model": manifest["model_name"], "representation": "D2", "top_k": 5},
        "generation_model": settings.openai_generation_model,
        "summary": {
            "pass_count": sum(case["passed"] for case in cases),
            "fail_count": sum(not case["passed"] for case in cases),
            "unsupported_madhhab_claim_cases": [case["id"] for case in cases if case["checks"]["unsupported_madhhab_mentions"]],
            "unsupported_claim_cases": [case["id"] for case in cases if case["checks"]["unsupported_external_escalation_instruction"]],
            "evidence_mutation_cases": [case["id"] for case in cases if not case["checks"]["displayed_evidence_exact"]],
            "evidence_leak_cases": [case["id"] for case in cases if case["checks"]["evidence_leaked_into_gpt_answer"]],
            "single_unit_answers": sum(case["final_structured_output"]["status"] == "ANSWER" and len(case["selected_ids"]) == 1 for case in cases),
            "multi_unit_answers": sum(case["final_structured_output"]["status"] == "ANSWER" and len(case["selected_ids"]) > 1 for case in cases),
        },
        "cases": cases,
    }
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    MD_PATH.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
