<script setup>
import { Head } from '@inertiajs/vue3';
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import AnswerCard from '../../components/AnswerCard.vue';
import Icon from '../../components/Icon.vue';
import Logo from '../../components/Logo.vue';
import PublicLayout from '../../layouts/PublicLayout.vue';
import { ApiError, aiOnline, ask as apiAsk, sendFeedback } from '../../lib/api.js';
import { failureText, fromApi, mockAnswer } from '../../lib/answers.js';
import { KB } from '../../lib/content.js';
import { toast } from '../../lib/ui.js';

defineOptions({ layout: PublicLayout });

/* ---------- State ---------- */
const thread = ref([]);
const busy = ref(false);
// Whether live answers are available. Not shown in the UI; when off, answers come from
// the small prepared set and each one says so in its footer.
const live = ref('checking'); // 'checking' | 'on' | 'off'
const draft = ref('');
const textarea = ref(null);
const threadEl = ref(null);
const rec = ref(null);
const micError = ref('');
let controller = null;
let uidCounter = 0;
const uid = () => `m${++uidCounter}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const hasExample = computed(() => thread.value.some((m) => m.example));

function ensureExample() {
    if (thread.value.length) return;
    thread.value.push({ role: 'user', id: 'ex0', text: 'هل صلاة الجمعة فرض عين؟', ch: 'text', example: true });
    thread.value.push({ role: 'bot', id: 'ex1', ...KB.jumuah_fard, latency: 2.1, mode: 'example', example: true });
}

async function scrollThread() {
    await nextTick();
    if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight;
}

/* ---------- Asking ---------- */
// After a live "needs clarification" answer, the next typed message continues that question.
function pendingClarification() {
    const last = [...thread.value].reverse().find((m) => m.role === 'bot' && !m.pending);
    return last && last.mode === 'live' && last.status === 'NEEDS_CLARIFICATION' && last.serverId ? last.serverId : null;
}

async function ask(q, ch = 'text', opts = {}) {
    q = String(q || '').trim();
    if (!q || busy.value) return;
    if (hasExample.value) thread.value = [];

    const parentId = opts.parentId ?? pendingClarification();
    thread.value.push({ role: 'user', id: uid(), text: q, ch, followUp: Boolean(parentId) });
    const bot = reactive({ role: 'bot', id: uid(), pending: true, ch, q, parentId, t0: performance.now(), elapsed: 0, live: false });
    thread.value.push(bot);
    busy.value = true;
    const useLive = live.value === 'on';
    bot.live = useLive;
    scrollThread();

    const tick = setInterval(() => (bot.elapsed = Math.floor((performance.now() - bot.t0) / 1000)), 500);
    let res;
    try {
        if (useLive) {
            res = await askLive(q, ch, parentId);
        } else {
            await sleep(800 + Math.random() * 700);
            res = { ...mockAnswer(q), mode: 'demo' };
        }
    } finally {
        clearInterval(tick);
    }

    const { id: serverId, ...rest } = res;
    Object.assign(bot, rest, { serverId: serverId ?? null, pending: false, latency: (performance.now() - bot.t0) / 1000 });
    delete bot.keys;
    delete bot.need;
    delete bot.min;
    busy.value = false;
    controller = null;
    scrollThread();
    if (window.matchMedia('(pointer:fine)').matches) nextTick(() => textarea.value?.focus());
}

async function askLive(q, ch, parentId) {
    controller = new AbortController();
    try {
        return fromApi(await apiAsk({ query: q, channel: ch, parentId, signal: controller.signal }));
    } catch (e) {
        if (e?.name === 'AbortError') return { status: 'FAILED', fail: 'أوقفتَ الإجابة قبل اكتمالها.', stopped: true, mode: 'live' };
        if (!(e instanceof ApiError)) {
            live.value = 'off';
            return { ...mockAnswer(q), mode: 'demo' };
        }
        return { id: e.body?.id, status: 'FAILED', fail: failureText(e), mode: 'live' };
    }
}

function submit() {
    const v = draft.value;
    if (!v.trim()) return textarea.value?.focus();
    draft.value = '';
    autosize();
    ask(v, 'text');
}

function onKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        submit();
    }
}

function autosize() {
    nextTick(() => {
        const ta = textarea.value;
        if (!ta) return;
        ta.style.height = 'auto';
        ta.style.height = Math.min(160, ta.scrollHeight) + 'px';
    });
}

function newChat() {
    controller?.abort();
    thread.value = [];
    busy.value = false;
    ensureExample();
}

/* ---------- Answer actions ---------- */
async function onFeedback(m, value) {
    m.fb = m.fb === value ? null : value;
    m.fbr = null;
    if (m.serverId) {
        try {
            await sendFeedback(m.serverId, m.fb);
        } catch {
            toast('تعذّر حفظ التقييم. حاول مرة أخرى.', 'info');
            return;
        }
    }
    if (m.fb === 'up') toast('شكراً، وصل تقييمك إلى فريق المراجعة.');
}

async function onReason(m, reason) {
    m.fbr = reason;
    if (m.serverId) {
        try {
            await sendFeedback(m.serverId, 'down', reason);
        } catch {
            toast('تعذّر حفظ التقييم. حاول مرة أخرى.', 'info');
            return;
        }
    }
    toast('شكراً، سيراجع الفريق هذه الإجابة.');
}

async function onCopy(m) {
    const text = [
        m.answer,
        m.explanation,
        ...(m.evidence || []).map((x) => x.text + (x.ref ? ' (' + x.ref + ')' : '')),
        ...(m.sources || []).map((x) => 'المصدر: الموسوعة الفقهية، ' + x.book + (x.chapter ? '، ' + x.chapter : '') + (x.href ? ' ' + x.href : '')),
    ]
        .filter(Boolean)
        .join('\n');
    try {
        await navigator.clipboard.writeText(text);
        toast('نُسخت الإجابة.');
    } catch {
        toast('تعذّر النسخ في هذا المتصفح. حدّد النص وانسخه يدوياً.', 'info');
    }
}

function onRetry(m) {
    ask(m.q, m.ch, { parentId: m.parentId });
}

function onClarify(m, option) {
    ask(option, 'text', { parentId: m.serverId });
}

/* ---------- Voice ----------
 * Speech is transcribed in the browser (Web Speech API, Arabic). When that is not
 * possible the visitor is told why, and nothing is sent. */
const MIC_MESSAGES = {
    'not-allowed': 'لا يمكن الوصول إلى الميكروفون. اسمح للموقع باستخدام الميكروفون من إعدادات المتصفح (رمز القفل بجانب العنوان)، ثم حاول مرة أخرى.',
    'service-not-allowed': 'لا يمكن الوصول إلى الميكروفون. اسمح للموقع باستخدام الميكروفون من إعدادات المتصفح (رمز القفل بجانب العنوان)، ثم حاول مرة أخرى.',
    'audio-capture': 'لم يُعثر على ميكروفون يعمل. تأكد من توصيله ومن أنه غير مستخدم في تطبيق آخر، ثم حاول مرة أخرى.',
    network: 'تعذّر الاتصال بخدمة التعرّف على الكلام في المتصفح. تحقق من اتصالك ثم حاول مرة أخرى.',
    unsupported: 'متصفحك لا يدعم السؤال بالصوت. استخدم Chrome أو Edge، أو اكتب سؤالك.',
};

function startRec() {
    if (busy.value || rec.value) return;
    micError.value = '';
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
        micError.value = MIC_MESSAGES.unsupported;
        return;
    }

    const r = reactive({ t0: Date.now(), text: '', seconds: 0 });
    try {
        const sr = new SR();
        sr.lang = 'ar-SA';
        sr.interimResults = true;
        sr.continuous = true;
        sr.onresult = (e) => {
            let t = '';
            for (const x of e.results) t += x[0].transcript;
            r.text = t;
        };
        sr.onerror = (e) => {
            if (rec.value !== r) return;
            if (e.error === 'no-speech') {
                stopRec(false);
                toast('لم يُلتقط أي كلام. حاول مرة أخرى.', 'mic-off');
            } else if (e.error !== 'aborted') {
                stopRec(false);
                micError.value = MIC_MESSAGES[e.error] || MIC_MESSAGES['not-allowed'];
            }
        };
        // The browser ends recognition by itself after a pause: send what was heard.
        sr.onend = () => {
            if (rec.value === r) stopRec(true);
        };
        r.sr = sr;
        rec.value = r;
        sr.start();
    } catch {
        rec.value = null;
        micError.value = MIC_MESSAGES['not-allowed'];
        return;
    }

    r.timer = setInterval(() => {
        if (rec.value !== r) return;
        r.seconds = Math.floor((Date.now() - r.t0) / 1000);
        if (r.seconds >= 20) stopRec(true);
    }, 200);
}

function stopRec(send) {
    const r = rec.value;
    if (!r) return;
    rec.value = null;
    clearInterval(r.timer);
    try {
        r.sr?.stop();
    } catch {
        // Already stopped.
    }
    if (!send) return;
    const text = r.text.trim();
    if (text) ask(text, 'voice');
    else toast('لم يُلتقط أي كلام. حاول مرة أخرى.', 'mic-off');
}

const bars = Array.from({ length: 28 }, (_, i) => `${((i * 73) % 900) / 1000}s`);

function onEscape(e) {
    if (e.key === 'Escape' && rec.value) stopRec(false);
}

/* ---------- Boot ---------- */
onMounted(async () => {
    window.addEventListener('keydown', onEscape);
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    if (!q) ensureExample();
    if (params.get('prefill')) {
        draft.value = params.get('prefill');
        nextTick(() => {
            textarea.value?.focus();
            textarea.value?.setSelectionRange(draft.value.length, draft.value.length);
        });
    }
    live.value = (await aiOnline()) ? 'on' : 'off';
    if (q) ask(q, 'text');
    if (params.get('voice')) startRec();
    scrollThread();
});

onBeforeUnmount(() => {
    window.removeEventListener('keydown', onEscape);
    if (rec.value) stopRec(false);
    controller?.abort();
});
</script>

<template>
    <Head title="اسأل دليل" />

    <div class="wrap try-grid solo">
        <section class="chat" aria-label="محادثة دليل">
            <div class="chat-head">
                <Icon name="message-square-text" />
                <h1>اسأل دليل</h1>
                <span class="grow" />
                <button class="btn btn-ghost btn-sm" type="button" @click="newChat"><Icon name="plus" />محادثة جديدة</button>
            </div>

            <div ref="threadEl" class="thread" aria-live="polite">
                <span v-if="hasExample" class="example-tag"><Icon name="info" size="xs" />مثال جاهز. اكتب سؤالك أو اسأل بصوتك.</span>
                <template v-for="m in thread" :key="m.id">
                    <div v-if="m.role === 'user'" class="qa-user enter">
                        {{ m.text }}
                        <div v-if="m.ch === 'voice'" class="meta"><Icon name="mic" size="xs" />سؤال صوتي</div>
                        <div v-else-if="m.followUp" class="meta"><Icon name="circle-question-mark" size="xs" />توضيح للسؤال السابق</div>
                    </div>
                    <div v-else-if="m.pending" :id="`ans-${m.id}`" class="ans enter">
                        <div class="pending">
                            <span class="spin-star"><Logo /></span>
                            <span>يبحث في الموسوعة الفقهية<span class="dots" aria-hidden="true"><i /><i /><i /></span><span class="num">{{ m.elapsed ? ` · ${m.elapsed} ث` : '' }}</span></span>
                            <button v-if="m.live" class="btn btn-outline btn-xs" type="button" style="margin-inline-start: auto" @click="controller?.abort()"><Icon name="square" size="xs" />إيقاف</button>
                        </div>
                        <div style="padding: 0 14px 16px; display: flex; flex-direction: column; gap: 8px">
                            <div class="skel" style="width: 92%" />
                            <div class="skel" style="width: 76%" />
                            <div class="skel" style="width: 54%" />
                        </div>
                    </div>
                    <AnswerCard v-else :m="m" @feedback="onFeedback" @reason="onReason" @copy="onCopy" @retry="onRetry" @clarify="onClarify" />
                </template>
            </div>

            <form class="composer" autocomplete="off" @submit.prevent="submit">
                <div v-if="micError" class="alert mic-alert" role="alert">
                    <Icon name="mic-off" />
                    <span class="alert-title">تعذّر السؤال بالصوت</span>
                    <span class="alert-desc">{{ micError }}</span>
                    <button class="icon-btn mic-alert-close" type="button" aria-label="إغلاق التنبيه" @click="micError = ''"><Icon name="x" size="sm" /></button>
                </div>
                <div class="comp-box">
                    <template v-if="rec">
                        <div class="recorder">
                            <span class="rec-dot" />
                            <span class="rec-time">0:{{ String(rec.seconds).padStart(2, '0') }}</span>
                            <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px">
                                <div class="wave" aria-hidden="true"><i v-for="(d, i) in bars" :key="i" :style="{ animationDelay: d }" /></div>
                                <div class="transcript">{{ rec.text || 'تحدّث الآن…' }}</div>
                            </div>
                        </div>
                        <button type="button" class="btn btn-ghost btn-icon" aria-label="إلغاء التسجيل" @click="stopRec(false)"><Icon name="x" /></button>
                        <button type="button" class="btn" @click="stopRec(true)"><Icon name="square" size="sm" />إيقاف وإرسال</button>
                    </template>
                    <template v-else>
                        <label class="sr-only" for="q">سؤالك</label>
                        <textarea
                            id="q"
                            ref="textarea"
                            v-model="draft"
                            rows="1"
                            placeholder="اكتب سؤالك الفقهي…"
                            :disabled="busy"
                            @input="autosize"
                            @keydown="onKeydown"
                        />
                        <button type="button" class="btn btn-ghost btn-icon mic-btn" aria-label="اسأل بصوتك" :disabled="busy" @click="startRec"><Icon name="mic" /></button>
                        <button type="submit" class="btn btn-icon" aria-label="إرسال" :disabled="busy"><Icon name="arrow-up" /></button>
                    </template>
                </div>
                <div class="comp-hint">
                    <span>دليل أداة بحث تعليمية، وإجاباته ليست فتوى رسمية.</span><span class="grow" />
                    <span class="only-desk" style="gap: 4px; align-items: center"><span class="kbd">Enter</span> للإرسال · <span class="kbd">Shift + Enter</span> لسطر جديد</span>
                </div>
            </form>
        </section>
    </div>
</template>
