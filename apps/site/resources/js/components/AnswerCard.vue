<script setup>
// The design's answer card (renderAnswer), one per bot turn.
import { computed } from 'vue';
import Icon from './Icon.vue';
import StBadge from './StBadge.vue';
import { FB_REASONS, bookUrl } from '../lib/content.js';

const props = defineProps({
    m: { type: Object, required: true },
    // Static cards (the home page example) show the controls but nothing is clickable.
    static: { type: Boolean, default: false },
});

const emit = defineEmits(['feedback', 'reason', 'copy', 'retry', 'clarify']);

const s = computed(() => props.m.status);
const nearSources = computed(() => (props.m.sources || []).some((x) => x.near));
const modeNote = computed(() =>
    props.m.mode === 'live' ? 'إجابة مباشرة من خدمة الإجابة' : props.m.mode === 'example' ? 'إجابة مُعدّة مسبقاً' : 'وضع العرض: إجابة مُعدّة',
);
const ordinals = ['الأول', 'الثاني', 'الثالث'];
</script>

<template>
    <article class="ans" :class="{ enter: !static }" :id="`ans-${m.id || 'x'}`">
        <div class="ans-head">
            <StBadge :state="s" />
            <span v-if="m.topic" class="muted" style="font-size: 0.8125rem">{{ m.topic }}</span>
            <span class="meta">
                <span v-if="m.latency" class="num"><Icon name="timer" size="xs" />{{ m.latency.toFixed(1) }} ث</span>
            </span>
        </div>

        <div class="ans-body">
            <div v-if="s === 'FAILED'" class="failbox">
                <div style="display: flex; gap: 8px; line-height: 1.7"><Icon name="triangle-alert" /><span>{{ m.fail || 'تعذّرت معالجة السؤال.' }}</span></div>
                <div v-if="!static && !m.stopped">
                    <button class="btn btn-outline btn-sm" type="button" @click="emit('retry', m)"><Icon name="refresh-cw" />أعد المحاولة</button>
                </div>
            </div>

            <template v-else>
                <p v-if="m.answer" class="ans-text">{{ m.answer }}</p>
                <p v-if="m.explanation" class="ans-text sub">{{ m.explanation }}</p>

                <div v-if="s === 'NEEDS_CLARIFICATION' && (m.clarifying_question || m.clarify_options?.length)" class="clarify">
                    <div class="q">{{ m.clarifying_question }}</div>
                    <div v-if="m.clarify_options?.length" class="ex-chips">
                        <button v-for="o in m.clarify_options" :key="o" class="chip" type="button" :disabled="static" @click="emit('clarify', m, o)">{{ o }}</button>
                    </div>
                    <span v-else-if="!static && m.mode === 'live'" class="help">اكتب التوضيح في مربع السؤال، وسيُرسل مع سؤالك الأول.</span>
                </div>

                <div v-if="s === 'CONFLICTING_EVIDENCE' && m.positions?.length" class="evid">
                    <span class="ans-label"><Icon name="git-compare" size="sm" />أقوال العلماء</span>
                    <div class="positions">
                        <div v-for="(p, i) in m.positions" :key="i" class="pos">
                            <span class="who">القول {{ ordinals[i] || '' }}<template v-if="p.held_by"> · {{ p.held_by }}</template></span>
                            <b>{{ p.view }}</b>
                            <span v-if="p.evidence" class="muted">{{ p.evidence }}</span>
                        </div>
                    </div>
                </div>

                <div v-if="s === 'COMPLEX_CASE' && m.refer_reasons?.length" class="refer">
                    <span class="ans-label" style="color: var(--foreground)"><Icon name="scale" size="sm" />لماذا نحيلك إلى مفتٍ</span>
                    <ul>
                        <li v-for="r in m.refer_reasons" :key="r">{{ r }}</li>
                    </ul>
                </div>

                <div v-if="m.suggest" class="alert">
                    <Icon name="info" /><span class="alert-title">الخطوة التالية</span><span class="alert-desc">{{ m.suggest }}</span>
                </div>

                <div v-if="m.evidence?.length" class="evid">
                    <span class="ans-label"><Icon name="quote" size="sm" />{{ m.mode === 'live' ? 'من نص الموسوعة' : 'الدليل' }}</span>
                    <div v-for="(e, i) in m.evidence" :key="i" class="quote" :class="{ para: !e.quoted }">
                        {{ e.text }}
                        <cite v-if="e.ref || e.href">
                            {{ e.ref }}
                            <a v-if="e.href" class="quote-link" :href="e.href" target="_blank" rel="noopener">اقرأه في موضعه<Icon name="external-link" size="xs" /></a>
                        </cite>
                    </div>
                </div>

                <div v-if="m.sources?.length" class="evid">
                    <span class="ans-label"><Icon name="book-marked" size="sm" />{{ nearSources ? 'أقرب الأبواب في الموسوعة' : 'المصدر' }}</span>
                    <div class="srcs">
                        <a v-for="(x, i) in m.sources" :key="i" class="src" :href="x.href || bookUrl(x.book)" target="_blank" rel="noopener">
                            الموسوعة الفقهية<span class="sep">›</span>{{ x.book }}<template v-if="x.chapter"><span class="sep">›</span>{{ x.chapter }}</template>
                            <Icon name="external-link" size="xs" />
                        </a>
                    </div>
                </div>

                <div v-if="m.link">
                    <a class="btn btn-outline btn-sm" :href="m.link.href" target="_blank" rel="noopener">{{ m.link.label }}<Icon name="external-link" size="sm" /></a>
                </div>
            </template>
        </div>

        <template v-if="!static && !m.stopped">
            <div class="ans-foot">
                <button
                    class="btn btn-ghost btn-icon btn-sm"
                    :class="{ 'fb-on': m.fb === 'up' }"
                    type="button"
                    :aria-pressed="m.fb === 'up'"
                    aria-label="إجابة مفيدة"
                    @click="emit('feedback', m, 'up')"
                >
                    <Icon name="thumbs-up" />
                </button>
                <button
                    class="btn btn-ghost btn-icon btn-sm"
                    :class="{ 'fb-on': m.fb === 'down' }"
                    type="button"
                    :aria-pressed="m.fb === 'down'"
                    aria-label="إجابة غير مفيدة"
                    @click="emit('feedback', m, 'down')"
                >
                    <Icon name="thumbs-down" />
                </button>
                <button v-if="s !== 'FAILED'" class="btn btn-ghost btn-sm" type="button" @click="emit('copy', m)"><Icon name="copy" />نسخ</button>
                <span class="note">{{ modeNote }}</span>
            </div>
            <div v-if="m.fb === 'down' && !m.fbr" class="fb-reasons">
                <span class="help" style="width: 100%">ما المشكلة في الإجابة؟</span>
                <button v-for="r in FB_REASONS.slice(0, 4)" :key="r.t" class="chip" type="button" @click="emit('reason', m, r.t)">{{ r.t }}</button>
            </div>
        </template>
        <div v-else-if="static" class="ans-foot">
            <span class="btn btn-ghost btn-icon btn-sm" aria-hidden="true"><Icon name="thumbs-up" /></span>
            <span class="btn btn-ghost btn-icon btn-sm" aria-hidden="true"><Icon name="thumbs-down" /></span>
            <span class="note">مثال توضيحي</span>
        </div>
    </article>
</template>
