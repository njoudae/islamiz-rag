<script setup>
import { Head } from '@inertiajs/vue3';
import { computed } from 'vue';
import Icon from '../../components/Icon.vue';
import StBadge from '../../components/StBadge.vue';
import AdminLayout from '../../layouts/AdminLayout.vue';
import { CONFUSION_NOTES, STATUS, ST_CLASSIFY } from '../../lib/content.js';
import { dLong, fmtN, fmtPct } from '../../lib/format.js';
import { toast } from '../../lib/ui.js';

defineOptions({ layout: AdminLayout });

const props = defineProps({
    pairs: { type: Array, required: true }, // [{ gold, predicted, n }] from reviews
    failures: { type: Array, required: true },
    failedTotal: { type: Number, required: true },
    feedbackReasons: { type: Array, required: true },
    reviewed: { type: Number, required: true },
    evalSize: { type: Number, required: true },
    citationAccuracy: { type: Object, required: true }, // { value, judged } from reviews
    versions: { type: Array, required: true }, // one per generation model seen in the log
    transcription: { type: Object, required: true }, // { wer, samples, terms }
});

/* Confusion matrix from the team's reviews: rows are the reviewer's label, columns the system's. */
const matrix = computed(() => {
    const m = ST_CLASSIFY.map(() => ST_CLASSIFY.map(() => 0));
    props.pairs.forEach((p) => {
        const r = ST_CLASSIFY.indexOf(p.gold);
        const c = ST_CLASSIFY.indexOf(p.predicted);
        if (r >= 0 && c >= 0) m[r][c] += p.n;
    });
    return m;
});

const stats = computed(() => {
    const m = matrix.value;
    let tot = 0;
    let diag = 0;
    m.forEach((r, i) => r.forEach((v, j) => {
        tot += v;
        if (i === j) diag += v;
    }));
    const row = (i) => m[i].reduce((a, b) => a + b, 0);
    return { tot, acc: tot ? diag / tot : NaN, clar: row(1) ? m[1][1] / row(1) : NaN, refer: row(3) ? m[3][3] / row(3) : NaN };
});

const rowSums = computed(() => matrix.value.map((r) => r.reduce((a, b) => a + b, 0)));

function cell(i, j) {
    const v = matrix.value[i][j];
    const p = rowSums.value[i] ? v / rowSums.value[i] : 0;
    const mix = Math.round(6 + p * 88);
    return {
        v,
        style: { background: `color-mix(in oklab, var(--seq) ${mix}%, var(--card))`, color: mix > 55 ? '#fff' : 'var(--foreground)' },
        tip: `المراجِع: <b>${STATUS[ST_CLASSIFY[i]].ar}</b><br>النموذج: <b>${STATUS[ST_CLASSIFY[j]].ar}</b><br>${v} سؤالاً · ${fmtPct(p)} من الصف`,
    };
}

const insights = computed(() => {
    const offs = [];
    matrix.value.forEach((r, i) => r.forEach((v, j) => {
        if (i !== j && v > 0) offs.push({ i, j, v });
    }));
    offs.sort((a, b) => b.v - a.v);
    return offs.slice(0, 4).map((o) => {
        const note = CONFUSION_NOTES[ST_CLASSIFY[o.i] + '>' + ST_CLASSIFY[o.j]] || { p: 'خلط متكرر بين النتيجتين.', fix: 'راجع أمثلة هذا الخلط وأضفها إلى تعليمات النموذج.' };
        return { ...o, gold: ST_CLASSIFY[o.i], predicted: ST_CLASSIFY[o.j], ...note };
    });
});

/* Version comparison: one column per generation model that has answered questions. */
const versionRows = [
    ['الأسئلة', 'questions', '', null],
    ['مراجعات بشرية', 'reviewed', '', null],
    ['دقة التصنيف', 'accuracy', '%', 'high'],
    ['دقة الاستشهاد', 'citation', '%', 'high'],
    ['الاستيضاح عند الحاجة', 'clarification', '%', 'high'],
    ['الإحالة الصحيحة', 'referral', '%', 'high'],
    ['زمن الإجابة p95', 'p95', ' ث', 'low'],
];
function best(key, better) {
    if (!better || props.versions.length < 2) return null;
    const vals = props.versions.map((v) => v[key]).filter((x) => x !== null);
    if (!vals.length) return null;
    return better === 'low' ? Math.min(...vals) : Math.max(...vals);
}
const cellText = (v, key, unit) => (v[key] === null ? '—' : unit ? Number(v[key]).toFixed(1) + unit : fmtN(v[key]));

const maxFailure = computed(() => Math.max(1, ...props.failures.map((f) => f.n)));
const feedbackTotal = computed(() => props.feedbackReasons.reduce((s, f) => s + f.n, 0));
const maxReason = computed(() => Math.max(1, ...props.feedbackReasons.map((f) => f.n)));

async function copyExport() {
    try {
        const response = await fetch('/admin/quality/export', { headers: { Accept: 'application/json' } });
        await navigator.clipboard.writeText(await response.text());
        toast('نُسخت مجموعة التقييم بصيغة JSON.');
    } catch {
        toast('تعذّر النسخ في هذا المتصفح. استخدم «تنزيل الملف».', 'info');
    }
}
</script>

<template>
    <Head title="جودة النموذج" />

    <div class="kpis" style="grid-template-columns: repeat(auto-fit, minmax(170px, 1fr))">
        <div class="card kpi"><span class="lbl"><Icon name="gauge" size="sm" />دقة التصنيف</span><span class="val">{{ fmtPct(stats.acc) }}</span><span class="help">من {{ fmtN(stats.tot) }} مراجعة بشرية</span></div>
        <div class="card kpi"><span class="lbl"><Icon name="book-marked" size="sm" />دقة الاستشهاد بالمصادر</span><span class="val">{{ fmtPct(citationAccuracy.value ?? NaN) }}</span><span class="help">من {{ fmtN(citationAccuracy.judged) }} إجابة تحقّق المراجِع من مصادرها</span></div>
        <div class="card kpi"><span class="lbl"><Icon name="circle-question-mark" size="sm" />الاستيضاح عند الحاجة</span><span class="val">{{ fmtPct(stats.clar) }}</span><span class="help">من الأسئلة الغامضة فعلاً</span></div>
        <div class="card kpi"><span class="lbl"><Icon name="layers" size="sm" />مجموعة التقييم</span><span class="val">{{ fmtN(evalSize) }}</span><span class="help">سؤالاً مراجَعاً</span></div>
    </div>

    <div class="grid-2">
        <section class="card">
            <div>
                <h2 class="card-title">مصفوفة التصنيف</h2>
                <p class="card-desc">كل صف هو النتيجة التي اختارها المراجِع، وكل عمود ما اختاره النموذج. القطر تصنيف صحيح، وما خارجه أخطاء. مراجعاتك في الطابور تُضاف هنا.</p>
            </div>
            <div class="mx-axis"><Icon name="arrow-left" size="xs" />الأعمدة: تصنيف النموذج · الصفوف: تصنيف المراجِع</div>
            <div class="matrix-wrap">
                <div class="matrix">
                    <div />
                    <div v-for="s in ST_CLASSIFY" :key="'h' + s" class="mx-h" :data-st="s"><Icon :name="STATUS[s].icon" size="sm" /><span>{{ STATUS[s].ar }}</span></div>
                    <template v-for="(row, i) in matrix" :key="'r' + i">
                        <div class="mx-r" :data-st="ST_CLASSIFY[i]"><span class="swatch" />{{ STATUS[ST_CLASSIFY[i]].ar }}</div>
                        <div v-for="(v, j) in row" :key="'c' + i + j" class="mx-c" :class="{ diag: i === j }" :style="cell(i, j).style" :data-tip="cell(i, j).tip">{{ v }}</div>
                    </template>
                </div>
            </div>
            <p class="help">«تعذّرت المعالجة» خطأ تقني لا يدخل في المصفوفة.</p>
        </section>

        <section class="card">
            <div>
                <h2 class="card-title">أكثر أخطاء التصنيف</h2>
                <p class="card-desc">مرتبة حسب العدد، مع اقتراح لكل منها.</p>
            </div>
            <div v-if="!insights.length" class="empty" style="padding: 24px 8px">
                <Icon name="gauge" size="lg" /><b style="color: var(--foreground)">لا أخطاء تصنيف بعد</b>
                <span style="line-height: 1.7">تظهر هنا حين يختار المراجِع نتيجة غير التي اختارها النموذج.</span>
            </div>
            <ul v-else class="insights">
                <li v-for="o in insights" :key="o.gold + o.predicted">
                    <span class="cnt">{{ o.v }}</span>
                    <span class="pair"><span class="muted">الصحيح</span><StBadge :state="o.gold" /><span class="muted">صنّفه النموذج</span><StBadge :state="o.predicted" /></span>
                    <p>{{ o.p }}</p>
                    <span class="fix"><Icon name="arrow-left" size="xs" /> {{ o.fix }}</span>
                </li>
            </ul>
        </section>
    </div>

    <div class="grid-2e">
        <section class="card">
            <div>
                <h2 class="card-title">مقارنة الإصدارات</h2>
                <p class="card-desc">عمود لكل نموذج توليد أجاب عن أسئلة فعلية، من الأقدم إلى الأحدث. الأرقام من سجل الأسئلة والمراجعات، والأفضل في كل صف بخط عريض.</p>
            </div>
            <div v-if="!versions.length" class="empty" style="padding: 24px 8px">
                <Icon name="layers" size="lg" /><b style="color: var(--foreground)">لا إصدارات بعد</b>
                <span style="line-height: 1.7">يُسجَّل اسم النموذج مع كل سؤال يجيب عنه، ويظهر هنا عمود له.</span>
            </div>
            <div v-else class="table-scroll">
                <table class="vtable">
                    <thead>
                        <tr>
                            <th>المقياس</th>
                            <th v-for="(v, i) in versions" :key="v.model" :class="{ cur: i === versions.length - 1 }" :data-tip="`أول سؤال: ${dLong.format(new Date(v.firstSeen))}`">
                                <span class="latin">{{ v.model }}</span>{{ i === versions.length - 1 ? ' (الحالي)' : '' }}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="[label, key, unit, better] in versionRows" :key="key">
                            <td>{{ label }}</td>
                            <td v-for="(v, i) in versions" :key="v.model" class="n" :class="{ cur: i === versions.length - 1 }" :style="v[key] !== null && v[key] === best(key, better) ? 'font-weight:700' : ''">
                                {{ cellText(v, key, unit) }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <section class="card">
            <div>
                <h2 class="card-title">أسباب الفشل</h2>
                <p class="card-desc">خلال 30 يوماً: {{ fmtN(failedTotal) }} سؤالاً لم يُعالج.</p>
            </div>
            <div v-if="!failures.length" class="help">لا فشل تقني خلال 30 يوماً.</div>
            <div v-else class="barlist">
                <div v-for="f in failures" :key="f.label" class="bl-row" data-st="FAILED">
                    <span>{{ f.label }}</span><span class="v">{{ fmtN(f.n) }} · {{ fmtPct(f.n / failedTotal, 0) }}</span>
                    <div class="bar"><i :style="{ width: (f.n / maxFailure) * 100 + '%' }" /></div>
                </div>
            </div>
            <hr class="separator" />
            <div>
                <h3 class="card-title" style="font-size: 0.9375rem">أسباب التقييم السلبي</h3>
                <p class="card-desc">ما يختاره السائل بعد «غير مفيدة»، خلال 30 يوماً.</p>
            </div>
            <div v-if="!feedbackReasons.length" class="help">لا تقييمات سلبية خلال 30 يوماً.</div>
            <div v-else class="barlist">
                <div v-for="f in feedbackReasons" :key="f.label" class="bl-row">
                    <span>{{ f.label }}</span><span class="v">{{ fmtPct(f.n / feedbackTotal, 0) }}</span>
                    <div class="bar"><i :style="{ width: (f.n / maxReason) * 100 + '%' }" /></div>
                </div>
            </div>
        </section>
    </div>

    <div class="grid-2e">
        <section class="card">
            <div>
                <h2 class="card-title">مصطلحات يخطئ التفريغ الصوتي فيها</h2>
                <p class="card-desc">
                    من {{ fmtN(transcription.samples) }} سؤالاً صوتياً مراجَعاً. نسبة خطأ التفريغ: <b class="num">{{ fmtPct(transcription.wer ?? NaN) }}</b>.
                    يصحّح المراجِع نص السؤال الصوتي في طابور المراجعة، فتُستخرج الكلمات المخطئة هنا.
                </p>
            </div>
            <div v-if="!transcription.terms.length" class="help">لا أخطاء تفريغ مسجّلة بعد.</div>
            <ul v-else class="terms">
                <li v-for="t in transcription.terms" :key="t.right + t.wrong"><b>{{ t.right }}</b><span class="arrow"><Icon name="arrow-left" size="xs" /></span><s>{{ t.wrong }}</s><span class="c">{{ t.n }} مرة</span></li>
            </ul>
        </section>

        <section class="card">
            <div>
                <h2 class="card-title">تصدير مجموعة التقييم</h2>
                <p class="card-desc">الأسئلة المراجَعة مع تصنيفها الصحيح وتصحيحاتها، لاختبار الإصدار القادم قبل إطلاقه.</p>
            </div>
            <dl class="kv">
                <dt>مراجعات محفوظة</dt><dd class="num">{{ fmtN(reviewed) }}</dd>
                <dt>منها في مجموعة التقييم</dt><dd class="num">{{ fmtN(evalSize) }}</dd>
                <dt>الصيغة</dt><dd>JSON</dd>
            </dl>
            <div style="display: flex; gap: 8px; flex-wrap: wrap">
                <a class="btn" href="/admin/quality/export" download><Icon name="download" />تنزيل الملف</a>
                <button class="btn btn-outline" type="button" @click="copyExport"><Icon name="copy" />نسخ JSON</button>
            </div>
        </section>
    </div>
</template>
