<script setup>
import { Head, Link, router, useForm } from '@inertiajs/vue3';
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import Icon from '../../components/Icon.vue';
import StBadge from '../../components/StBadge.vue';
import AdminLayout from '../../layouts/AdminLayout.vue';
import { STATUS, ST_ORDER } from '../../lib/content.js';
import { agoAr, fmtN, minutesSince } from '../../lib/format.js';

defineOptions({ layout: AdminLayout });

const props = defineProps({
    questions: { type: Object, required: true }, // paginated: { data, links, meta }
    filters: { type: Object, required: true },
    tabCounts: { type: Object, required: true },
    kpis: { type: Object, required: true },
});

/* ---------- Filters (applied on the server) ---------- */
const f = reactive({ ...props.filters, search: props.filters.search ?? '' });

function apply() {
    const query = { filter: f.filter, state: f.state, channel: f.channel, search: f.search || undefined };
    router.get('/admin/review', query, { preserveState: true, preserveScroll: true, replace: true, only: ['questions', 'filters', 'tabCounts'] });
}

let searchTimer;
watch(
    () => f.search,
    () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(apply, 300);
    },
);

function setTab(id) {
    f.filter = id;
    apply();
}

function setChannel(v) {
    f.channel = v;
    apply();
}

/* ---------- Review sheet ---------- */
const open = ref(null);
const firstRadio = ref(null);
const form = useForm({ verdict: '', label: '', citation_correct: null, correction: '', transcript_correction: '', add_to_eval: true });
const verdictMissing = ref(false);

function openReview(item) {
    open.value = item;
    form.defaults({
        verdict: item.review?.verdict || '',
        label: item.review?.label || item.state,
        citation_correct: item.review?.citation_correct ?? null,
        correction: item.review?.correction || '',
        transcript_correction: item.review?.transcript_correction || '',
        add_to_eval: item.review ? item.review.add_to_eval : true,
    });
    form.reset();
    form.clearErrors();
    verdictMissing.value = false;
    nextTick(() => firstRadio.value?.focus());
}

function closeSheet() {
    open.value = null;
}

function save() {
    if (!form.verdict) {
        verdictMissing.value = true;
        return;
    }
    form.post(`/admin/review/${open.value.id}`, {
        preserveScroll: true,
        preserveState: true,
        onSuccess: () => closeSheet(),
    });
}

const onKey = (e) => {
    if (e.key === 'Escape' && open.value) closeSheet();
};
onMounted(() => window.addEventListener('keydown', onKey));
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));

const feedbackText = (it) => (it.feedback ? (it.feedback === 'up' ? 'مفيدة' : 'غير مفيدة') + (it.feedback_reason ? ' · ' + it.feedback_reason : '') : 'لم يقيّم');
const verdicts = [
    ['correct', 'صحيحة'],
    ['edit', 'تحتاج تعديلاً'],
    ['wrong', 'خاطئة'],
];
const items = computed(() => props.questions.data);
</script>

<template>
    <Head title="طابور المراجعة" />

    <div class="view-intro">
        <p>كل سؤال وصل إلى خدمة الإجابة، من الأحدث إلى الأقدم: التقييمات السلبية والإحالات وما لم يجد دليلاً وما فشل تقنياً. كل مراجعة تُضاف إلى مجموعة التقييم وتُحدّث مصفوفة التصنيف.</p>
    </div>

    <div class="kpis" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))">
        <div class="card kpi"><span class="lbl"><span class="kchip"><Icon name="inbox" size="sm" /></span>بانتظار المراجعة</span><span v-count-up class="val">{{ fmtN(kpis.pending) }}</span></div>
        <div class="card kpi"><span class="lbl"><span class="kchip"><Icon name="thumbs-down" size="sm" /></span>تقييم سلبي</span><span v-count-up class="val">{{ fmtN(kpis.negative) }}</span></div>
        <div class="card kpi" data-tip="إجابات قُدّمت مع أن أفضل مقطع مطابق حصل على أقل من 70%"><span class="lbl"><span class="kchip"><Icon name="gauge" size="sm" /></span>ثقة أقل من 70%</span><span v-count-up class="val">{{ fmtN(kpis.lowConfidence) }}</span></div>
        <div class="card kpi"><span class="lbl"><span class="kchip"><Icon name="check" size="sm" /></span>راجعتها اليوم</span><span v-count-up class="val">{{ fmtN(kpis.reviewedToday) }}</span></div>
    </div>

    <section class="card">
        <div class="q-tools">
            <div class="tabs" role="tablist">
                <button
                    v-for="[id, label] in [['pending', 'بانتظار المراجعة'], ['done', 'تمت المراجعة'], ['all', 'الكل']]"
                    :key="id"
                    class="tab"
                    type="button"
                    role="tab"
                    :aria-selected="f.filter === id"
                    @click="setTab(id)"
                >
                    {{ label }}<span class="count">{{ tabCounts[id] }}</span>
                </button>
            </div>
            <div class="select-wrap" style="width: 180px">
                <label class="sr-only" for="qSt">النتيجة</label>
                <select id="qSt" v-model="f.state" class="select" @change="apply">
                    <option value="ALL">كل النتائج</option>
                    <option v-for="s in ST_ORDER" :key="s" :value="s">{{ STATUS[s].ar }}</option>
                </select>
                <Icon name="chevron-down" size="sm" />
            </div>
            <div class="seg" role="group" aria-label="القناة">
                <button v-for="[v, l] in [['all', 'الكل'], ['voice', 'صوت'], ['text', 'نص']]" :key="v" type="button" :aria-pressed="f.channel === v" @click="setChannel(v)">{{ l }}</button>
            </div>
            <div class="search">
                <label class="sr-only" for="qSearch">ابحث في الأسئلة</label><Icon name="search" />
                <input id="qSearch" v-model="f.search" class="input" placeholder="ابحث في نص السؤال" />
            </div>
        </div>

        <div v-if="!items.length" class="empty">
            <Icon name="inbox" size="lg" /><b style="color: var(--foreground)">لا توجد أسئلة بهذه المرشحات</b><span>غيّر النتيجة أو القناة، أو امسح البحث.</span>
        </div>
        <div v-else class="table-scroll">
            <table class="qtable">
                <thead>
                    <tr><th>السؤال</th><th>النتيجة</th><th>الثقة</th><th>تقييم السائل</th><th>الوقت</th><th /></tr>
                </thead>
                <tbody>
                    <tr v-for="it in items" :key="it.id" tabindex="0" @click="openReview(it)" @keydown.enter.prevent="openReview(it)" @keydown.space.prevent="openReview(it)">
                        <td class="c-q">
                            <div class="qtext"><template v-if="it.channel === 'voice'"><Icon name="mic" size="xs" /> </template>{{ it.query }}</div>
                            <div class="sub">
                                <span v-if="it.is_demo" class="badge">توضيحي</span>
                                <span class="reason">{{ it.reason }}</span><span>· {{ it.chapter || it.source || '—' }}</span>
                            </div>
                        </td>
                        <td><StBadge :state="it.state" /></td>
                        <td class="c-hide">
                            <span v-if="it.state === 'FAILED' || it.confidence === null" class="muted">—</span>
                            <span v-else class="meter" data-tip="درجة مطابقة أفضل مقطع للسؤال">
                                <span class="meter-track" style="width: 40px"><span class="meter-fill" :class="{ low: it.confidence < 70 }" :style="{ width: it.confidence + '%' }" /></span>
                                <span class="num">{{ it.confidence }}%</span>
                            </span>
                        </td>
                        <td class="c-hide">
                            <span v-if="it.feedback" class="fbi" :class="it.feedback">
                                <Icon :name="it.feedback === 'up' ? 'thumbs-up' : 'thumbs-down'" size="xs" />{{ it.feedback_reason || (it.feedback === 'up' ? 'مفيدة' : 'غير مفيدة') }}
                            </span>
                            <span v-else class="muted">—</span>
                        </td>
                        <td class="c-hide" style="white-space: nowrap; color: var(--muted-foreground)">{{ agoAr(minutesSince(it.created_at)) }}</td>
                        <td>
                            <span v-if="it.review" class="rv-done"><Icon name="check" size="xs" />روجعت</span>
                            <button v-else class="btn btn-outline btn-xs" type="button" @click.stop="openReview(it)">مراجعة</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <nav v-if="questions.meta.last_page > 1" class="pager" aria-label="ترقيم الصفحات">
            <component :is="questions.links.prev ? Link : 'span'" :href="questions.links.prev" preserve-scroll class="btn btn-outline btn-sm" :class="{ 'is-disabled': !questions.links.prev }" :style="questions.links.prev ? '' : 'opacity:.4'">السابق</component>
            <span class="num">صفحة {{ questions.meta.current_page }} من {{ questions.meta.last_page }} · {{ fmtN(questions.meta.total) }} سؤالاً</span>
            <component :is="questions.links.next ? Link : 'span'" :href="questions.links.next" preserve-scroll class="btn btn-outline btn-sm" :style="questions.links.next ? '' : 'opacity:.4'">التالي</component>
        </nav>
    </section>

    <template v-if="open">
        <div class="overlay" @click="closeSheet" />
        <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="sh-t">
            <div class="sheet-head">
                <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px">
                    <h2 id="sh-t">مراجعة سؤال</h2>
                    <div><StBadge :state="open.state" code /></div>
                </div>
                <button class="icon-btn" type="button" aria-label="إغلاق" @click="closeSheet"><Icon name="x" /></button>
            </div>
            <form class="sheet-body" @submit.prevent="save">
                <div style="font-size: 1.0625rem; line-height: 1.8; font-weight: 500">{{ open.query }}</div>
                <dl class="kv">
                    <template v-if="open.context"><dt>السؤال السابق</dt><dd>{{ open.context }}</dd></template>
                    <dt>القناة</dt><dd>{{ open.channel === 'voice' ? 'صوت (مفرّغ إلى نص)' : 'نص' }}</dd>
                    <dt>سبب الإدراج</dt><dd>{{ open.reason }}</dd>
                    <dt>الكتاب</dt><dd>{{ open.book || '—' }}</dd>
                    <dt>الفصل</dt><dd>{{ open.chapter || '—' }}</dd>
                    <dt>درجة المطابقة</dt><dd class="num">{{ open.confidence === null || open.state === 'FAILED' ? '—' : open.confidence + '%' }}</dd>
                    <template v-if="open.state_reason"><dt>سبب التصنيف</dt><dd dir="ltr" style="text-align: right" class="latin">{{ open.state_reason }}</dd></template>
                    <template v-if="open.model_name"><dt>نموذج التوليد</dt><dd dir="ltr" style="text-align: right" class="latin">{{ open.model_name }}</dd></template>
                    <dt>تقييم السائل</dt><dd>{{ feedbackText(open) }}</dd>
                    <dt>مدة المعالجة</dt><dd class="num">{{ open.duration_ms ? (open.duration_ms / 1000).toFixed(1) + ' ث' : '—' }}</dd>
                    <dt>الوقت</dt><dd>{{ agoAr(minutesSince(open.created_at)) }}</dd>
                    <template v-if="open.review?.by"><dt>آخر مراجعة</dt><dd>{{ open.review.by }}</dd></template>
                </dl>
                <div class="evid">
                    <span class="ans-label"><Icon name="message-square-text" size="sm" />إجابة النموذج كما ظهرت للسائل</span>
                    <div class="quote para">{{ open.model || '—' }}</div>
                </div>
                <div v-if="open.sources.length" class="srcs">
                    <a v-for="(s, i) in open.sources" :key="i" class="src" :href="s.url" target="_blank" rel="noopener">{{ s.title }}<Icon name="external-link" size="xs" /></a>
                </div>
                <hr class="separator" />
                <fieldset class="field" style="border: 0; padding: 0; margin: 0">
                    <legend class="label">حكمك على الإجابة</legend>
                    <div class="radio-row">
                        <label v-for="([k, l], i) in verdicts" :key="k">
                            <input :ref="i === 0 ? (el) => (firstRadio = el) : undefined" v-model="form.verdict" type="radio" name="verdict" :value="k" @change="verdictMissing = false" />{{ l }}
                        </label>
                    </div>
                    <span v-if="verdictMissing || form.errors.verdict" class="err">{{ form.errors.verdict || 'اختر حكماً على الإجابة قبل الحفظ.' }}</span>
                </fieldset>
                <div class="field">
                    <label class="label" for="rvLabel">النتيجة الصحيحة</label>
                    <div class="select-wrap">
                        <select id="rvLabel" v-model="form.label" class="select">
                            <option v-for="s in ST_ORDER" :key="s" :value="s">{{ STATUS[s].ar }} · {{ s }}</option>
                        </select>
                        <Icon name="chevron-down" size="sm" />
                    </div>
                    <span class="help">إن اختلفت عن نتيجة النموذج، تُسجَّل في مصفوفة التصنيف.</span>
                </div>
                <fieldset v-if="open.sources.length" class="field" style="border: 0; padding: 0; margin: 0">
                    <legend class="label">هل المصادر المستشهد بها تدعم الإجابة؟</legend>
                    <div class="radio-row">
                        <label><input v-model="form.citation_correct" type="radio" name="citation" :value="true" />نعم</label>
                        <label><input v-model="form.citation_correct" type="radio" name="citation" :value="false" />لا</label>
                        <label><input v-model="form.citation_correct" type="radio" name="citation" :value="null" />لم أتحقق</label>
                    </div>
                    <span class="help">تُحسب منها دقة الاستشهاد في صفحة جودة النموذج.</span>
                </fieldset>
                <div v-if="open.channel === 'voice'" class="field">
                    <label class="label" for="rvTranscript">ما قاله السائل فعلاً</label>
                    <textarea id="rvTranscript" v-model="form.transcript_correction" class="textarea" rows="2" placeholder="اكتب نص السؤال الصحيح إن أخطأ التفريغ الصوتي" />
                    <span class="help">اتركه فارغاً إن كان التفريغ صحيحاً. تُحسب منه نسبة خطأ التفريغ والمصطلحات التي يخطئ فيها.</span>
                </div>
                <div class="field">
                    <label class="label" for="rvFix">الإجابة المصحّحة أو الملاحظة</label>
                    <textarea id="rvFix" v-model="form.correction" class="textarea" rows="3" placeholder="اكتب الإجابة الصحيحة أو ما ينقص إجابة النموذج" />
                </div>
                <label class="check"><input v-model="form.add_to_eval" type="checkbox" />أضفه إلى مجموعة التقييم</label>
            </form>
            <div class="sheet-foot">
                <button class="btn" type="button" :disabled="form.processing" @click="save"><Icon name="check" />حفظ المراجعة</button>
                <button class="btn btn-outline" type="button" @click="closeSheet">إلغاء</button>
            </div>
        </aside>
    </template>
</template>
