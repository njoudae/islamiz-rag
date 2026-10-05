// Formatting helpers, as in the design.

const nf = new Intl.NumberFormat('en-US');

export const fmtN = (n) => nf.format(Math.round(n || 0));
export const fmtPct = (x, d = 1) => (Number.isFinite(x) ? (x * 100).toFixed(d) + '%' : '—');
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export const dShort = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', { day: 'numeric', month: 'short' });
export const dLong = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', { day: 'numeric', month: 'long', year: 'numeric' });
export const dHijri = new Intl.DateTimeFormat('ar-SA-u-ca-islamic-umalqura-nu-latn', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

/** HTML-escape, for the few strings that end up in tooltip markup. */
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

/** Arabic-aware normalisation used for client-side search and the offline demo matcher. */
export function norm(s) {
    return String(s || '')
        .replace(/[ً-ْٰـ]/g, '')
        .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه')
        .replace(/[؟،؛«»"'()[\]{}.,!?:;\-–—_/\\]/g, ' ')
        .replace(/\s+/g, ' ').trim();
}

/** "قبل 5 دقائق" style relative time, from minutes ago. */
export function agoAr(min) {
    min = Math.max(0, Math.round(min));
    if (min < 1) return 'الآن';
    if (min < 60) return min === 1 ? 'قبل دقيقة' : min === 2 ? 'قبل دقيقتين' : min <= 10 ? `قبل ${min} دقائق` : `قبل ${min} دقيقة`;
    const h = Math.round(min / 60);
    if (h < 24) return h === 1 ? 'قبل ساعة' : h === 2 ? 'قبل ساعتين' : h <= 10 ? `قبل ${h} ساعات` : `قبل ${h} ساعة`;
    const d = Math.round(h / 24);
    return d === 1 ? 'قبل يوم' : d === 2 ? 'قبل يومين' : `قبل ${d} أيام`;
}

export const minutesSince = (iso) => (iso ? (Date.now() - new Date(iso).getTime()) / 60000 : 0);

export const booksAr = (n) => (n === 1 ? 'كتاب واحد' : n === 2 ? 'كتابان' : n <= 10 ? `${n} كتب` : `${n} كتاباً`);

export const periodAr = (p) => (p === 7 ? '7 أيام' : p === 30 ? '30 يوماً' : '90 يوماً');
