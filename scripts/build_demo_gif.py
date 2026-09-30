"""Build the README demo GIF from the latest persisted real browser pipeline trace."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "artifacts" / "generation" / "latest_pipeline_trace.json"
OUTPUT = ROOT / "docs" / "assets" / "daleel-demo.gif"

ARABIC_FORMS = {
    "ء": ("\ufe80",), "آ": ("\ufe81", "\ufe82"), "أ": ("\ufe83", "\ufe84"),
    "ؤ": ("\ufe85", "\ufe86"), "إ": ("\ufe87", "\ufe88"), "ئ": ("\ufe89", "\ufe8a", "\ufe8b", "\ufe8c"),
    "ا": ("\ufe8d", "\ufe8e"), "ب": ("\ufe8f", "\ufe90", "\ufe91", "\ufe92"),
    "ة": ("\ufe93", "\ufe94"), "ت": ("\ufe95", "\ufe96", "\ufe97", "\ufe98"),
    "ث": ("\ufe99", "\ufe9a", "\ufe9b", "\ufe9c"), "ج": ("\ufe9d", "\ufe9e", "\ufe9f", "\ufea0"),
    "ح": ("\ufea1", "\ufea2", "\ufea3", "\ufea4"), "خ": ("\ufea5", "\ufea6", "\ufea7", "\ufea8"),
    "د": ("\ufea9", "\ufeaa"), "ذ": ("\ufeab", "\ufeac"), "ر": ("\ufead", "\ufeae"),
    "ز": ("\ufeaf", "\ufeb0"), "س": ("\ufeb1", "\ufeb2", "\ufeb3", "\ufeb4"),
    "ش": ("\ufeb5", "\ufeb6", "\ufeb7", "\ufeb8"), "ص": ("\ufeb9", "\ufeba", "\ufebb", "\ufebc"),
    "ض": ("\ufebd", "\ufebe", "\ufebf", "\ufec0"), "ط": ("\ufec1", "\ufec2", "\ufec3", "\ufec4"),
    "ظ": ("\ufec5", "\ufec6", "\ufec7", "\ufec8"), "ع": ("\ufec9", "\ufeca", "\ufecb", "\ufecc"),
    "غ": ("\ufecd", "\ufece", "\ufecf", "\ufed0"), "ف": ("\ufed1", "\ufed2", "\ufed3", "\ufed4"),
    "ق": ("\ufed5", "\ufed6", "\ufed7", "\ufed8"), "ك": ("\ufed9", "\ufeda", "\ufedb", "\ufedc"),
    "ل": ("\ufedd", "\ufede", "\ufedf", "\ufee0"), "م": ("\ufee1", "\ufee2", "\ufee3", "\ufee4"),
    "ن": ("\ufee5", "\ufee6", "\ufee7", "\ufee8"), "ه": ("\ufee9", "\ufeea", "\ufeeb", "\ufeec"),
    "و": ("\ufeed", "\ufeee"), "ى": ("\ufeef", "\ufef0"), "ي": ("\ufef1", "\ufef2", "\ufef3", "\ufef4"),
}


def shape_arabic(text: str) -> str:
    """Minimal presentation-form shaping for Pillow builds without libraqm."""
    chars = list(text)
    shaped: list[str] = []
    for index, char in enumerate(chars):
        forms = ARABIC_FORMS.get(char)
        if not forms:
            shaped.append(char)
            continue
        previous = ARABIC_FORMS.get(chars[index - 1]) if index else None
        following = ARABIC_FORMS.get(chars[index + 1]) if index + 1 < len(chars) else None
        joins_previous = previous is not None and len(previous) == 4 and len(forms) > 1
        joins_following = following is not None and len(forms) == 4 and len(following) > 1
        if joins_previous and joins_following:
            shaped.append(forms[3])
        elif joins_previous:
            shaped.append(forms[1])
        elif joins_following:
            shaped.append(forms[2])
        else:
            shaped.append(forms[0])
    return "".join(shaped)[::-1]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(fonts / name), size)


def frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1200, 675), "#f7faf7")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((55, 42, 1145, 625), radius=28, fill="#ffffff", outline="#cfe0d8", width=2)
    draw.text((1090, 70), shape_arabic("دليل"), font=font(34, True), fill="#073f37", anchor="ra")
    draw.text((110, 76), "REAL RAG · VERIFIED BROWSER TRACE", font=font(19, True), fill="#16866f", anchor="la")
    return image, draw


def rtl(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, *, bold: bool = False, fill: str = "#15352f") -> None:
    draw.text(xy, shape_arabic(text), font=font(size, bold), fill=fill, anchor="ra")


def main() -> None:
    trace = json.loads(TRACE.read_text(encoding="utf-8"))
    question = trace["question"]
    answer = trace["frontend_response"]["summary"]
    citation = trace["citation_validation"]["citations"][0]
    top = trace["retrieved_chunks"][0]
    reranked = trace["reranked_chunks"][0]
    trace_id = trace["trace_id"]

    frames: list[Image.Image] = []

    image, draw = frame()
    rtl(draw, (1080, 155), "سؤال جديد عبر واجهة التطبيق", 28, bold=True)
    draw.rounded_rectangle((125, 215, 1075, 365), radius=20, fill="#eef8f4")
    rtl(draw, (1035, 268), question, 31)
    rtl(draw, (1035, 410), "تم الإرسال من واجهة التطبيق المحلية", 21, fill="#58736d")
    frames.append(image)

    image, draw = frame()
    rtl(draw, (1080, 145), "جارٍ بناء إجابة موثقة…", 29, bold=True)
    stages = [
        "PostgreSQL · real Dorar corpus",
        f"E5 + hybrid retrieval · document {top['fatwa_id']} · rank {top['fused_rank']}",
        f"Qwen reranker · document {reranked['fatwa_id']} · score {reranked['reranker_score']:.4f}",
        "Evidence Gate → OpenAI GPT → citation validation",
    ]
    for index, value in enumerate(stages):
        y = 225 + index * 78
        draw.ellipse((1010, y - 5, 1030, y + 15), fill="#159579")
        draw.text((165, y + 10), value, font=font(24), fill="#15352f", anchor="la")
    frames.append(image)

    image, draw = frame()
    rtl(draw, (1080, 145), "الإجابة المبنية على المصدر", 29, bold=True)
    draw.rounded_rectangle((115, 195, 1085, 390), radius=22, fill="#eaf8f3", outline="#9fd8c8", width=2)
    rtl(draw, (1035, 255), "أدلة كافية · استشهاد صالح", 21, bold=True, fill="#08745f")
    rtl(draw, (1035, 325), answer, 29)
    rtl(draw, (1035, 455), "لا مصدر = لا إجابة", 22, bold=True, fill="#08745f")
    draw.text((165, 505), f"trace: {trace_id}", font=font(17), fill="#71847f", anchor="la")
    frames.append(image)

    image, draw = frame()
    rtl(draw, (1080, 145), "المصدر الأصلي الموثق", 29, bold=True)
    draw.rounded_rectangle((115, 195, 1085, 465), radius=22, fill="#f4f8f6", outline="#b8cec7", width=2)
    rtl(draw, (1035, 245), "الموسوعة الفقهية – الدرر السنية", 23, bold=True, fill="#08745f")
    rtl(draw, (1035, 305), citation["title"], 29, bold=True)
    draw.text((165, 365), f"Dorar document ID: {citation['fatwa_id']}", font=font(23), fill="#15352f", anchor="la")
    draw.text((165, 420), citation["source_url"], font=font(16), fill="#316c61", anchor="la")
    draw.text((165, 520), "Persisted real result: artifacts/generation", font=font(20), fill="#58736d", anchor="la")
    frames.append(image)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=[1800, 1800, 2800, 2800],
        loop=0,
        optimize=True,
    )
    print(OUTPUT.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
