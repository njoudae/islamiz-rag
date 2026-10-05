<script setup>
import { Head, Link, useForm, usePage } from '@inertiajs/vue3';
import { computed, ref } from 'vue';
import Icon from '../../components/Icon.vue';
import PublicLayout from '../../layouts/PublicLayout.vue';
import { visitorId } from '../../lib/api.js';
import { toast } from '../../lib/ui.js';

defineOptions({ layout: PublicLayout });

const props = defineProps({
    topics: { type: Array, required: true },
    contactEmail: { type: String, required: true },
    messageMax: { type: Number, default: 1500 },
});

const IFTA_URL = 'https://www.alifta.gov.sa';

const page = usePage();
const blank = () => ({
    name: '',
    email: '',
    topic: props.topics[0]?.value ?? '',
    related_question: '',
    message: '',
    send_copy: false,
    website: '',
    visitor_id: visitorId(),
});
const form = useForm(blank());
const sent = ref(false);
const sentNow = computed(() => sent.value || page.props.flash?.contactSent === true);
const count = computed(() => form.message.length);

function submit() {
    form.post('/contact', {
        preserveScroll: true,
        onSuccess: () => {
            sent.value = true;
            form.defaults(blank());
            form.reset();
        },
    });
}

function another() {
    sent.value = false;
    page.props.flash.contactSent = false;
}

async function copyEmail() {
    try {
        await navigator.clipboard.writeText(props.contactEmail);
        toast('نُسخ البريد الإلكتروني.');
    } catch {
        toast('تعذّر النسخ في هذا المتصفح.', 'info');
    }
}

const faqs = [
    {
        q: 'هل دليل جهة إفتاء رسمية؟',
        a: 'لا. دليل أداة بحث تعليمية تعرض ما في الموسوعة الفقهية بأدلته ومصادره، ولا يصدر فتاوى. للفتوى الرسمية في مسألتك ارجع إلى الرئاسة العامة للبحوث العلمية والإفتاء.',
    },
    {
        q: 'من أين تأتي الإجابات؟',
        a: 'من الموسوعة الفقهية في موقع الدرر السنية. يبحث دليل في موادها، ويعرض الدليل ورابط الباب الذي أخذ منه، وإن لم يجد ما يكفي للإجابة قال ذلك بوضوح بدل أن يخمّن.',
    },
    {
        q: 'وجدت خطأ في إجابة، ماذا أفعل؟',
        a: 'اضغط «غير مفيدة» تحت الإجابة واختر السبب، أو أرسل لنا من هذه الصفحة بموضوع «الإبلاغ عن خطأ في إجابة» مع نص السؤال. يراجع فريق المراجعة الإجابة ويصحح تصنيفها.',
    },
    {
        q: 'هل تُحفظ أسئلتي؟',
        a: 'نعم. نحفظ نص السؤال ونتيجته وتقييمك لها مع معرّف مجهول لمتصفحك، دون اسم أو حساب، ليراجعها الفريق ويحسّن الإجابات. أما رسائل هذه الصفحة فنحفظها مع اسمك وبريدك لنرد عليك.',
    },
];
</script>

<template>
    <Head title="تواصل معنا" />

    <div class="wrap">
        <div class="enc-head" style="padding-top: 32px">
            <div style="display: flex; flex-direction: column; gap: 12px; min-width: 0">
                <span class="eyebrow"><Icon name="mail" />تواصل معنا</span>
                <h1 class="h1" style="font-size: clamp(1.75rem, 1.3rem + 2vw, 2.5rem)">راسل فريق دليل</h1>
                <p class="lead">أرسل لنا ملاحظتك، أو أبلغ عن إجابة رأيت فيها خطأ، أو اقترح مصدراً علمياً. يقرأ رسائلك فريق المراجعة الشرعية والتقنية.</p>
            </div>
        </div>

        <div class="contact-grid">
            <section class="card" aria-labelledby="contact-form-title">
                <div v-if="sentNow" class="contact-done" role="status">
                    <span class="st" data-st="ANSWERABLE"><Icon name="circle-check" />وصلت رسالتك</span>
                    <h2 id="contact-form-title" class="card-title" style="font-size: 1.125rem">شكراً لتواصلك مع دليل</h2>
                    <p class="muted" style="line-height: 1.8">سيقرأ الفريق رسالتك، وإن احتاجت رداً فسيصلك على بريدك الإلكتروني.</p>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap">
                        <button class="btn btn-outline" type="button" @click="another">إرسال رسالة أخرى</button>
                        <Link class="btn btn-ghost" href="/ask">اسأل دليل<Icon name="arrow-left" /></Link>
                    </div>
                </div>

                <template v-else>
                    <div>
                        <h2 id="contact-form-title" class="card-title" style="font-size: 1.125rem">أرسل رسالة</h2>
                        <p class="card-desc">الحقول المعلّمة بـ * مطلوبة.</p>
                    </div>
                    <form novalidate style="display: flex; flex-direction: column; gap: 16px" @submit.prevent="submit">
                        <div class="form-row">
                            <div class="field">
                                <label class="label" for="c-name">الاسم *</label>
                                <input id="c-name" v-model="form.name" class="input" autocomplete="name" maxlength="100" required :aria-invalid="form.errors.name ? 'true' : undefined" aria-describedby="c-name-err" />
                                <span v-if="form.errors.name" id="c-name-err" class="err">{{ form.errors.name }}</span>
                            </div>
                            <div class="field">
                                <label class="label" for="c-email">البريد الإلكتروني *</label>
                                <input id="c-email" v-model="form.email" class="input" type="email" dir="ltr" placeholder="name@example.com" autocomplete="email" maxlength="190" required :aria-invalid="form.errors.email ? 'true' : undefined" aria-describedby="c-email-err" />
                                <span v-if="form.errors.email" id="c-email-err" class="err">{{ form.errors.email }}</span>
                            </div>
                        </div>

                        <div class="field">
                            <label class="label" for="c-topic">الموضوع</label>
                            <div class="select-wrap">
                                <select id="c-topic" v-model="form.topic" class="select" :aria-invalid="form.errors.topic ? 'true' : undefined" aria-describedby="c-topic-err">
                                    <option v-for="t in topics" :key="t.value" :value="t.value">{{ t.label }}</option>
                                </select>
                                <Icon name="chevron-down" size="sm" />
                            </div>
                            <span v-if="form.errors.topic" id="c-topic-err" class="err">{{ form.errors.topic }}</span>
                        </div>

                        <div class="field">
                            <label class="label" for="c-question">السؤال الذي سألته في دليل</label>
                            <input id="c-question" v-model="form.related_question" class="input" maxlength="1000" placeholder="الصق نص السؤال حتى نجد الإجابة بسرعة" aria-describedby="c-question-help c-question-err" />
                            <span id="c-question-help" class="help">اختياري، لكنه يسرّع المراجعة.</span>
                            <span v-if="form.errors.related_question" id="c-question-err" class="err">{{ form.errors.related_question }}</span>
                        </div>

                        <div class="field">
                            <label class="label" for="c-message">الرسالة *</label>
                            <textarea id="c-message" v-model="form.message" class="textarea" rows="6" :maxlength="messageMax" required placeholder="اكتب ملاحظتك بالتفصيل" :aria-invalid="form.errors.message ? 'true' : undefined" aria-describedby="c-message-count c-message-err" />
                            <span id="c-message-count" class="char-count" :class="{ over: count >= messageMax }">{{ count }} / {{ messageMax }}</span>
                            <span v-if="form.errors.message" id="c-message-err" class="err">{{ form.errors.message }}</span>
                        </div>

                        <label class="check"><input v-model="form.send_copy" type="checkbox" />أرسل لي نسخة على بريدي</label>

                        <!-- Honeypot: hidden from people and screen readers. -->
                        <div class="hp-field" aria-hidden="true">
                            <label for="c-website">الموقع الإلكتروني</label>
                            <input id="c-website" v-model="form.website" tabindex="-1" autocomplete="off" />
                        </div>

                        <div v-if="form.hasErrors && !form.errors.name && !form.errors.email && !form.errors.topic && !form.errors.message && !form.errors.related_question" class="err" role="alert">
                            تعذّر الإرسال. حاول مرة أخرى بعد قليل.
                        </div>
                        <div>
                            <button class="btn btn-lg" type="submit" :disabled="form.processing"><Icon name="mail" />{{ form.processing ? 'جارٍ الإرسال…' : 'إرسال الرسالة' }}</button>
                        </div>
                    </form>
                </template>
            </section>

            <aside class="side">
                <div class="card">
                    <div class="card-title">البريد الإلكتروني</div>
                    <div class="mail-chip">
                        <Icon name="mail" />
                        <code>{{ contactEmail }}</code>
                        <button class="btn btn-outline btn-xs" type="button" @click="copyEmail"><Icon name="copy" size="xs" />نسخ</button>
                    </div>
                    <p class="help">للرسائل الطويلة أو المرفقات.</p>
                </div>

                <div class="card card-muted">
                    <div class="card-title" style="display: flex; gap: 8px; align-items: center"><Icon name="scale" />تريد فتوى في مسألتك؟</div>
                    <p class="muted" style="line-height: 1.8">لا نجيب عن الاستفتاءات عبر هذا النموذج. للفتوى الرسمية ارجع إلى الرئاسة العامة للبحوث العلمية والإفتاء.</p>
                    <div><a class="btn btn-outline btn-sm" :href="IFTA_URL" target="_blank" rel="noopener">موقع الرئاسة العامة للإفتاء<Icon name="external-link" size="sm" /></a></div>
                </div>

                <div class="card">
                    <div class="card-title">لديك سؤال فقهي عام؟</div>
                    <p class="muted" style="line-height: 1.8">اسأله في دليل، وستحصل على الحكم ودليله ومصدره من الموسوعة.</p>
                    <div><Link class="btn btn-sm" href="/ask">اسأل دليل<Icon name="arrow-left" /></Link></div>
                </div>
            </aside>
        </div>

        <section class="faq" aria-labelledby="faq-title">
            <h2 id="faq-title" class="h3">أسئلة شائعة</h2>
            <details v-for="f in faqs" :key="f.q">
                <summary>{{ f.q }}<Icon name="chevron-down" /></summary>
                <p>{{ f.a }}</p>
            </details>
        </section>
    </div>
</template>
