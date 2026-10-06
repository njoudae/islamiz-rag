<script setup>
import { Head, Link } from '@inertiajs/vue3';
import { computed, ref } from 'vue';
import Delta from '../../components/Delta.vue';
import Icon from '../../components/Icon.vue';
import LineChart from '../../components/LineChart.vue';
import Sparkline from '../../components/Sparkline.vue';
import StBadge from '../../components/StBadge.vue';
import AdminLayout from '../../layouts/AdminLayout.vue';
import { STATE_COLOR, actionHref, aggregate, ratio, series } from '../../lib/admin.js';
import { STATUS, ST_BAR, ST_ORDER } from '../../lib/content.js';
import { agoAr, fmtN, fmtPct, minutesSince, periodAr } from '../../lib/format.js';

defineOptions({ layout: AdminLayout });

const props = defineProps({
    period: { type: Number, required: true },
    days: { type: Array, required: true }, // previous window, then current window
    latency: { type: Object, required: true },
    recent: { type: Array, required: true },
    messages: { type: Array, default: () => [] }, // newest contact-page messages
    newMessages: { type: Number, default: 0 }, // shared: how many are still unread
    sections: { type: Array, default: () => [] }, // questions per encyclopedia section
    transcription: { type: Object, default: () => ({ wer: null, samples: 0 }) },
    events: { type: Array, default: () => [] }, // [{ date, label }] to mark on the trend chart
    hasDemoData: { type: Boolean, default: false },
});

const A = computed(() => aggregate(props.days.slice(props.period)));
const B = computed(() => aggregate(props.days.slice(0, props.period)));
const cur = computed(() => A.value.days);

const kpis = computed(() => {
    const a = A.value;
    const b = B.value;
    return [
        { label: 'إجمالي الأسئلة', icon: 'message-square-text', value: fmtN(a.total), cur: a.total, prev: b.total, opts: { pct: true }, spark: series(cur.value, (d) => d.total) },
        { label: 'الإجابة المباشرة', icon: 'circle-check', value: fmtPct(ratio(a.c.ANSWERABLE, a.total)), cur: ratio(a.c.ANSWERABLE, a.total), prev: ratio(b.c.ANSWERABLE, b.total), opts: { pp: true }, spark: series(cur.value, (d) => d.c.ANSWERABLE, (d) => d.total) },
        { label: 'رضا المستخدمين', icon: 'thumbs-up', value: fmtPct(ratio(a.up, a.rated), 0), cur: ratio(a.up, a.rated), prev: ratio(b.up, b.rated), opts: { pp: true }, spark: series(cur.value, (d) => d.up, (d) => d.rated) },
        { label: 'معدل الفشل', icon: 'triangle-alert', value: fmtPct(ratio(a.c.FAILED, a.total)), cur: ratio(a.c.FAILED, a.total), prev: ratio(b.c.FAILED, b.total), opts: { pp: true, goodUp: false }, spark: series(cur.value, (d) => d.c.FAILED, (d) => d.total) },
        { label: 'الأسئلة الصوتية', icon: 'mic', value: fmtPct(ratio(a.voice, a.total), 0), cur: ratio(a.voice, a.total), prev: ratio(b.voice, b.total), opts: { pp: true }, spark: series(cur.value, (d) => d.voice, (d) => d.total) },
    ];
});

const p50 = computed(() => props.latency.current.p50);
const p95 = computed(() => props.latency.current.p95);

const rows = computed(() =>
    ST_ORDER.map((s) => ({
        s,
        count: A.value.c[s],
        share: ratio(A.value.c[s], A.value.total),
        prevShare: ratio(B.value.c[s], B.value.total),
        neutral: s === 'CONFLICTING_EVIDENCE' || s === 'COMPLEX_CASE',
        goodUp: s === 'ANSWERABLE',
        spark: series(cur.value, (d) => d.c[s], (d) => d.total),
    })),
);

const stackTip = (s) => `<b>${STATUS[s].ar}</b><br>${fmtN(A.value.c[s])} سؤالاً · ${fmtPct(ratio(A.value.c[s], A.value.total))}`;

/* Trend chart */
const trendState = ref('ANSWERABLE');
const trendMode = ref('share');
const trend = computed(() => {
    const share = trendMode.value === 'share';
    const s = trendState.value;
    return {
        values: cur.value.map((d) => (share ? (d.total ? d.c[s] / d.total : 0) : d.c[s])),
        dates: cur.value.map((d) => new Date(d.date + 'T12:00:00')),
        format: share ? (v) => (v * 100).toFixed(v < 0.1 && v > 0 ? 1 : 0) + '%' : (v) => fmtN(v),
    };
});
// Model changes and outage days, placed on the day they happened.
const annotations = computed(() =>
    props.events
        .map((e) => ({ i: cur.value.findIndex((d) => d.date === e.date), label: e.label }))
        .filter((a) => a.i >= 0),
);

/* Voice and text */
const text = computed(() => A.value.total - A.value.voice);
const voiceShare = computed(() => ratio(A.value.voice, A.value.total));

const maxSection = computed(() => Math.max(1, ...props.sections.map((s) => s.total)));
</script>

<template>
    <Head title="نظرة عامة" />

    <div class="kpis">
        <div v-for="k in kpis" :key="k.label" class="card kpi">
            <span class="lbl"><span class="kchip"><Icon :name="k.icon" size="sm" /></span>{{ k.label }}</span>
            <span class="val">{{ k.value }}</span>
            <div class="row"><Delta :cur="k.cur" :prev="k.prev" v-bind="k.opts" /><Sparkline :values="k.spark" /></div>
        </div>
        <div class="card kpi">
            <span class="lbl"><span class="kchip"><Icon name="timer" size="sm" /></span>زمن الإجابة (الوسيط)</span>
            <span class="val">{{ p50 === null ? '—' : p50.toFixed(1) }}<small v-if="p50 !== null">ث</small></span>
            <div class="row">
                <Delta :cur="p50" :prev="latency.previous.p50" :good-up="false" unit=" ث" />
                <span class="help num">p95 {{ p95 === null ? '—' : p95.toFixed(1) + ' ث' }}</span>
            </div>
        </div>
    </div>
    <p class="help" style="margin-top: -6px">
        مقارنة بالـ{{ periodAr(period) }} السابقة. الأرقام من سجل الأسئلة الفعلي<template v-if="hasDemoData">، ويتضمن صفوفاً توضيحية أُنشئت لعرض اللوحة</template>.
    </p>

    <section class="card" aria-labelledby="dist-t">
        <div class="card-head">
            <div>
                <h2 id="dist-t" class="card-title">نتائج الأسئلة وما يُفعل بكل منها</h2>
                <p class="card-desc">كل نتيجة تشير إلى نوع مختلف من التحسين. ابدأ بأكبر نسبة قابلة للتحسين.</p>
            </div>
        </div>
        <div class="stack" role="img" aria-label="توزيع الأسئلة على النتائج السبع">
            <span v-for="s in ST_BAR" :key="s" :data-st="s" :style="{ flex: A.c[s] }" :data-tip="stackTip(s)" />
        </div>
        <div class="table-scroll">
            <table class="st-table">
                <thead>
                    <tr><th>النتيجة</th><th>الأسئلة</th><th>النسبة</th><th>التغيّر</th><th>الاتجاه</th><th>ما يُفعل</th></tr>
                </thead>
                <tbody>
                    <tr v-for="r in rows" :key="r.s">
                        <td>
                            <div class="name">
                                <span class="swatch" :data-st="r.s" /><Icon :name="STATUS[r.s].icon" />
                                <span><b>{{ STATUS[r.s].ar }}</b><br /><span class="latin">{{ r.s }}</span></span>
                            </div>
                        </td>
                        <td class="n">{{ fmtN(r.count) }}</td>
                        <td class="n">{{ fmtPct(r.share) }}</td>
                        <td class="n"><Delta :cur="r.share" :prev="r.prevShare" pp :good-up="r.goodUp" :neutral="r.neutral" /></td>
                        <td><Sparkline :values="r.spark" /></td>
                        <td style="min-width: 220px">
                            <span class="help" style="display: block; color: var(--foreground); line-height: 1.6">{{ STATUS[r.s].admin }}</span>
                            <Link class="act-link" :href="actionHref(r.s)">{{ STATUS[r.s].actLabel }}<Icon name="arrow-left" size="xs" /></Link>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>

    <div class="grid-2">
        <section class="card" aria-labelledby="tr-t">
            <div class="card-head">
                <div>
                    <h2 id="tr-t" class="card-title">الاتجاه اليومي: {{ STATUS[trendState].ar }}</h2>
                    <p class="card-desc">الخطوط العمودية تحدد يوم تغيّر نموذج التوليد، والأيام التي فشل فيها نصف الأسئلة أو أكثر.</p>
                </div>
                <div class="chart-tools">
                    <div class="select-wrap" style="width: 170px">
                        <label class="sr-only" for="trendSt">النتيجة</label>
                        <select id="trendSt" v-model="trendState" class="select" style="height: 28px">
                            <option v-for="s in ST_ORDER" :key="s" :value="s">{{ STATUS[s].ar }}</option>
                        </select>
                        <Icon name="chevron-down" size="sm" />
                    </div>
                    <div class="seg" role="group" aria-label="المقياس">
                        <button type="button" :aria-pressed="trendMode === 'share'" @click="trendMode = 'share'">النسبة</button>
                        <button type="button" :aria-pressed="trendMode === 'count'" @click="trendMode = 'count'">العدد</button>
                    </div>
                </div>
            </div>
            <LineChart :values="trend.values" :dates="trend.dates" :format="trend.format" :color="STATE_COLOR[trendState]" :name="STATUS[trendState].ar" :annotations="annotations" />
        </section>

        <section class="card" aria-labelledby="live-t">
            <div class="card-head">
                <div>
                    <h2 id="live-t" class="card-title">أحدث الأسئلة</h2>
                    <p class="card-desc">آخر ما وصل من صفحة السؤال، كما صنّفه النموذج.</p>
                </div>
                <Link v-if="recent.length" class="btn btn-outline btn-sm" href="/admin/review?filter=all">في الطابور</Link>
            </div>
            <div v-if="!recent.length" class="empty" style="padding: 24px 8px">
                <Icon name="message-square-text" size="lg" />
                <b style="color: var(--foreground)">لا أسئلة بعد</b>
                <span style="line-height: 1.7">اطرح سؤالاً في صفحة السؤال، وسيظهر هنا مع تصنيفه وتقييم السائل.</span>
                <Link class="btn btn-outline btn-sm" href="/ask">افتح صفحة السؤال</Link>
            </div>
            <ul v-else class="feed">
                <li v-for="l in recent" :key="l.id">
                    <Icon :name="l.channel === 'voice' ? 'mic' : 'keyboard'" size="sm" />
                    <div class="q">
                        <div>{{ l.query }}</div>
                        <div class="m">
                            <StBadge :state="l.state" />
                            <span>{{ agoAr(minutesSince(l.created_at)) }}</span>
                            <span v-if="l.feedback" class="fbi" :class="l.feedback">
                                <Icon :name="l.feedback === 'up' ? 'thumbs-up' : 'thumbs-down'" size="xs" />{{ l.feedback_reason || '' }}
                            </span>
                            <span v-if="l.is_demo">توضيحي</span>
                        </div>
                    </div>
                </li>
            </ul>
        </section>
    </div>

    <section class="card" aria-labelledby="msg-t">
        <div class="card-head">
            <div>
                <h2 id="msg-t" class="card-title" style="display: flex; gap: 8px; align-items: center">
                    رسائل التواصل <span v-if="newMessages" class="badge badge-dark">{{ fmtN(newMessages) }} جديدة</span>
                </h2>
                <p class="card-desc">أحدث ما أرسله الزوار من صفحة «تواصل معنا».</p>
            </div>
            <Link class="btn btn-outline btn-sm" href="/admin/messages">افتح صندوق الرسائل</Link>
        </div>
        <div v-if="!messages.length" class="empty" style="padding: 24px 8px">
            <Icon name="mail" size="lg" /><b style="color: var(--foreground)">لا رسائل بعد</b>
            <span style="line-height: 1.7">تظهر هنا رسائل الزوار فور إرسالها.</span>
        </div>
        <ul v-else class="feed">
            <li v-for="m in messages" :key="m.id">
                <Icon name="mail" size="sm" />
                <div class="q">
                    <div :style="{ fontWeight: m.status === 'new' ? 600 : 400 }">{{ m.message }}</div>
                    <div class="m">
                        <span class="badge">{{ m.topic_label }}</span>
                        <span>{{ m.name }}</span>
                        <span>{{ agoAr(minutesSince(m.created_at)) }}</span>
                        <span v-if="m.status === 'new'" class="badge badge-dark">جديدة</span>
                    </div>
                </div>
            </li>
        </ul>
    </section>

    <div class="grid-2e">
        <section class="card">
            <div>
                <h2 class="card-title">الصوت مقابل النص</h2>
                <p class="card-desc">الأسئلة الصوتية تُفرّغ في المتصفح قبل إرسالها.</p>
            </div>
            <div class="stack" style="height: 12px">
                <span :style="{ flex: A.voice, '--c': 'var(--primary)' }" :data-tip="`صوت · ${fmtPct(voiceShare, 0)}`" />
                <span :style="{ flex: text, '--c': 'var(--gold)' }" :data-tip="`نص · ${fmtPct(1 - voiceShare, 0)}`" />
            </div>
            <div class="legend">
                <span><span class="swatch" style="--c: var(--primary)" />صوت {{ fmtPct(voiceShare, 0) }}</span>
                <span><span class="swatch" style="--c: var(--gold)" />نص {{ fmtPct(1 - voiceShare, 0) }}</span>
            </div>
            <table class="vtable">
                <thead><tr><th /><th>صوت</th><th>نص</th></tr></thead>
                <tbody>
                    <tr><td>الأسئلة</td><td class="n">{{ fmtN(A.voice) }}</td><td class="n">{{ fmtN(text) }}</td></tr>
                    <tr><td>معدل الفشل</td><td class="n" style="color: var(--bad-text)">{{ fmtPct(ratio(A.voiceFailed, A.voice)) }}</td><td class="n">{{ fmtPct(ratio(A.textFailed, text)) }}</td></tr>
                    <tr>
                        <td>نسبة خطأ التفريغ (WER)</td>
                        <td class="n" :data-tip="`محسوبة من ${transcription.samples} سؤالاً صوتياً صحّح المراجِع نصّه`">{{ fmtPct(transcription.wer ?? NaN) }}</td>
                        <td class="n">—</td>
                    </tr>
                </tbody>
            </table>
            <Link class="act-link" href="/admin/quality">مصطلحات يخطئ التفريغ فيها<Icon name="arrow-left" size="xs" /></Link>
        </section>

        <section class="card">
            <div>
                <h2 class="card-title">الأبواب الأكثر سؤالاً</h2>
                <p class="card-desc">الأسئلة التي وجد لها النموذج مادة قريبة في الفهرس، حسب الفصل، ونسبة ما أُجيب منها مباشرة.</p>
            </div>
            <div v-if="!sections.length" class="empty" style="padding: 24px 8px">
                <Icon name="library" size="lg" /><b style="color: var(--foreground)">لا بيانات بعد</b>
                <span style="line-height: 1.7">يظهر الفصل حين تطابق مادة مفهرسة سؤال الزائر.</span>
            </div>
            <div v-else class="barlist">
                <div v-for="b in sections" :key="b.book + b.chapter" class="bl-row" :data-tip="b.book">
                    <span>{{ b.chapter }}</span><span class="v">{{ fmtN(b.total) }} · {{ fmtPct(ratio(b.answered, b.total), 0) }} مباشرة</span>
                    <div class="bar"><i :style="{ width: (b.total / maxSection) * 100 + '%' }" /></div>
                </div>
            </div>
            <Link class="act-link" href="/admin/gaps">تغطية الفهرس<Icon name="arrow-left" size="xs" /></Link>
        </section>
    </div>
</template>
