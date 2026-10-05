// Turns answers into the shape the design's answer card renders.
import { DEMO_RESP, KB } from './content.js';
import { norm } from './format.js';

/** Map a response from POST /api/v1/ask onto the answer card. */
export function fromApi(p) {
    const citations = Array.isArray(p.citations) ? p.citations : [];
    const base = {
        id: p.id,
        status: p.state,
        topic: '',
        answer: '',
        explanation: '',
        evidence: [],
        sources: [],
        mode: 'live',
    };

    if (p.state === 'ANSWERABLE') {
        const first = citations[0];
        return {
            ...base,
            topic: first?.title || '',
            answer: p.summary || '',
            explanation: p.explanation || '',
            // The cited passage from the encyclopedia, with its own references when it has them.
            evidence: citations
                .filter((c) => c.excerpt)
                .slice(0, 2)
                .map((c) => ({
                    text: c.excerpt.length > 420 ? c.excerpt.slice(0, 420).trim() + '…' : c.excerpt,
                    ref: (c.original_reference || []).map((r) => r.raw).filter(Boolean).join('، ') || c.source_collection_name || '',
                    quoted: false,
                })),
            sources: citations.map((c) => ({ book: c.title, href: c.source_url })),
        };
    }

    if (p.state === 'NEEDS_CLARIFICATION') {
        return { ...base, clarifying_question: p.clarification_question || '', clarify_options: [] };
    }

    return { ...base, answer: p.escalation_message || '' };
}

/** The design's prepared answer for a preset key. */
export const prepared = (key) => ({ ...(KB[key] || DEMO_RESP[key]) });

/**
 * The design's offline matcher: a small set of prepared answers, used only when
 * the AI service is unavailable. Answers produced here are labelled as demo mode.
 */
export function mockAnswer(q) {
    const t = ' ' + norm(q) + ' ';
    const words = norm(q).split(' ').filter(Boolean);
    const has = (list) => list.some((k) => t.includes(norm(k)));
    if (has(['جوال', 'هاتف', 'ايفون', 'سامسونج', 'كاميرا', 'برمجة', 'طقس', 'مباراة', 'دوري', 'فيلم', 'مسلسل', 'وصفة', 'طبخ', 'سيارة جديدة', 'لابتوب', 'سعر الدولار', 'افضل تطبيق'])) return prepared('oos_general');
    if (has(['تفسير', 'معنى قوله', 'العرش', 'صحة حديث', 'درجة حديث', 'تخريج', 'العقيدة'])) return prepared('oos_creed');
    if (has(['ميراث', 'الميراث', 'التركة', 'تركة', 'الورثة', 'ورثة', 'الارث'])) return prepared('complex_inherit');
    if (has(['حلف بالطلاق', 'حلفت بالطلاق', 'طلقني', 'طلقها', 'طلقت', 'نذرت', 'حلف', 'حلفت'])) return prepared('complex_generic');
    if (has(['عملات رقمية', 'العملات الرقمية', 'بيتكوين', 'كريبتو', 'العملات المشفرة'])) return prepared('insuff_crypto');
    let best = null;
    let bestScore = 0;
    for (const [k, e] of Object.entries(KB)) {
        if (e.need && !e.need.some((n) => t.includes(norm(n)))) continue;
        const score = e.keys.filter((x) => t.includes(norm(x))).length;
        if (score >= (e.min || 2) && score > bestScore) {
            best = k;
            bestScore = score;
        }
    }
    if (best) return prepared(best);
    if (words.length <= 3) return prepared(has(['جمع', 'الجمع']) ? 'clarify_jam' : 'clarify_generic');
    return prepared('insuff_generic');
}

/** Visitor-facing text for API failures. */
export function failureText(error) {
    if (error?.status === 429) return 'أُرسلت أسئلة كثيرة في وقت قصير. انتظر قليلاً ثم أعد المحاولة.';
    if (error?.status === 422) return 'تعذّر إرسال السؤال. اكتب سؤالاً من ثلاثة أحرف على الأقل.';
    return error?.body?.message || 'تعذّر الاتصال بخدمة الإجابة. أعد المحاولة بعد قليل.';
}
