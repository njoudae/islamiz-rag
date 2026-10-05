// Helpers shared by the admin pages.
import { STATUS, ST_ORDER } from './content.js';

/** Where each outcome's "what to do" link leads. */
export function actionHref(state) {
    const s = STATUS[state];
    if (s.actFilter) return `/admin/review?state=${s.actFilter}`;
    return { admin: '/admin', 'admin-review': '/admin/review', 'admin-gaps': '/admin/gaps', 'admin-quality': '/admin/quality' }[s.actRoute] || '/admin';
}

export const STATE_COLOR = {
    ANSWERABLE: 'var(--st-ans)',
    CONFLICTING_EVIDENCE: 'var(--st-conf)',
    NEEDS_CLARIFICATION: 'var(--st-clar)',
    COMPLEX_CASE: 'var(--st-cplx)',
    INSUFFICIENT_EVIDENCE: 'var(--st-insuf)',
    OUT_OF_SCOPE: 'var(--st-oos)',
    FAILED: 'var(--st-fail)',
};

/** Sum a list of daily rows from the server into one period. */
export function aggregate(days) {
    const a = { total: 0, voice: 0, voiceFailed: 0, textFailed: 0, rated: 0, up: 0, c: {}, days };
    ST_ORDER.forEach((s) => (a.c[s] = 0));
    days.forEach((d) => {
        a.total += d.total;
        a.voice += d.voice;
        a.voiceFailed += d.voiceFailed;
        a.textFailed += d.textFailed;
        a.rated += d.rated;
        a.up += d.up;
        ST_ORDER.forEach((s) => (a.c[s] += d.c[s] || 0));
    });
    return a;
}

/** a / b, or NaN when there is nothing to divide by. */
export const ratio = (a, b) => (b ? a / b : NaN);

/**
 * Down-sample daily rows to at most maxPts points. Ratios are computed per bucket
 * from summed numerators and denominators, so quiet days do not distort them.
 */
export function series(days, num, den = null, maxPts = 20) {
    const step = Math.max(1, Math.ceil(days.length / maxPts));
    const out = [];
    for (let i = 0; i < days.length; i += step) {
        const chunk = days.slice(i, i + step);
        const n = chunk.reduce((s, d) => s + num(d), 0);
        if (!den) out.push(n / chunk.length);
        else {
            const dd = chunk.reduce((s, d) => s + den(d), 0);
            out.push(dd ? n / dd : NaN);
        }
    }
    return out;
}
