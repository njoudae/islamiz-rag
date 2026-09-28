import re
from app.models.domain import FatwaChunk, FatwaDocument


def structure_aware_chunks(document: FatwaDocument, max_chars: int = 2200) -> list[FatwaChunk]:
    base = "\n\n".join(part for part in [document.title, document.question, document.answer] if part)
    dialogue = [f"{turn.speaker}: {turn.text}" for turn in document.follow_up_dialogue]
    units = [base, *dialogue]
    if len(base) <= max_chars and not dialogue:
        units = [base]
    else:
        expanded: list[str] = []
        for unit in units:
            if len(unit) <= max_chars:
                expanded.append(unit)
                continue
            paragraphs = re.split(r"\n{2,}", unit)
            current = ""
            for paragraph in paragraphs:
                candidate = f"{current}\n\n{paragraph}".strip()
                if current and len(candidate) > max_chars:
                    expanded.append(current)
                    current = paragraph
                else:
                    current = candidate
            if current:
                expanded.append(current)
        units = expanded
    return [FatwaChunk(
        fatwa_id=document.external_id,
        title=document.title,
        content=content,
        category_path=document.category_path,
        source_url=document.canonical_url,
        chunk_index=index,
        source_collection=document.source_collection,
        source_author=document.source_author,
        source_authority=document.source_authority,
    ) for index, content in enumerate(units)]
