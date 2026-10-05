<script setup>
import { Link, router, usePage } from '@inertiajs/vue3';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import Icon from '../components/Icon.vue';
import Logo from '../components/Logo.vue';
import ThemeButton from '../components/ThemeButton.vue';
import Toasts from '../components/Toasts.vue';
import { dHijri, dLong } from '../lib/format.js';

const page = usePage();
const path = computed(() => page.url.split('?')[0].replace(/\/$/, '') || '/admin');
const user = computed(() => page.props.auth?.user);
const pending = computed(() => page.props.pendingReviews ?? 0);
const newMessages = computed(() => page.props.newMessages ?? 0);

const NAV = [
    ['/admin', 'نظرة عامة', 'layout-dashboard'],
    ['/admin/review', 'طابور المراجعة', 'inbox'],
    ['/admin/gaps', 'فجوات المعرفة', 'file-search'],
    ['/admin/quality', 'جودة النموذج', 'gauge'],
];
const INBOX = ['/admin/messages', 'رسائل التواصل', 'mail'];
const title = computed(() => ([...NAV, INBOX].find(([href]) => href === path.value) || NAV[0])[1]);

// The 7/30/90-day switch only applies to the pages that aggregate over time.
const showPeriod = computed(() => path.value === '/admin' || path.value === '/admin/gaps');
const period = computed(() => page.props.period ?? 30);
function setPeriod(p) {
    router.get(path.value, { period: p }, { preserveScroll: true, preserveState: true, replace: true });
}

// Header badge: shown only when synthetic questions were seeded into the log.
const demoBadge = computed(() => (page.props.hasDemoData ? 'بيانات توضيحية' : null));

// What the AI service reports about itself: model names and the real index size.
const kb = computed(() => page.props.knowledge);
const indexedOn = computed(() => (kb.value?.indexedAt ? dLong.format(new Date(kb.value.indexedAt)) : null));

const now = new Date();
const dateLine = `${dHijri.format(now)} · ${dLong.format(now)}`;

// The sidebar (with its logout button) appears from 1024px; below that the header carries logout.
const narrow = ref(false);
const measure = () => (narrow.value = window.innerWidth < 1024);
onMounted(() => {
    measure();
    window.addEventListener('resize', measure);
});
onBeforeUnmount(() => window.removeEventListener('resize', measure));

const logout = () => router.post('/logout');
</script>

<template>
    <div class="admin">
        <aside class="sidebar" aria-label="لوحة الإدارة">
            <div class="sb-brand">
                <span class="logo"><Logo /></span><span><b>دليل</b><span>لوحة الإدارة</span></span>
            </div>
            <div class="sb-label">تحسين النموذج</div>
            <nav style="display: flex; flex-direction: column; gap: 2px">
                <Link v-for="[href, label, icon] in NAV" :key="href" class="side-link" :href="href" :aria-current="path === href ? 'page' : undefined">
                    <Icon :name="icon" />{{ label }}<span v-if="href === '/admin/review'" class="badge">{{ pending }}</span>
                </Link>
            </nav>
            <div class="sb-label">التواصل</div>
            <nav style="display: flex; flex-direction: column; gap: 2px">
                <Link class="side-link" :href="INBOX[0]" :aria-current="path === INBOX[0] ? 'page' : undefined">
                    <Icon :name="INBOX[2]" />{{ INBOX[1] }}<span class="badge">{{ newMessages }}</span>
                </Link>
            </nav>
            <div class="sb-label">الموقع</div>
            <nav style="display: flex; flex-direction: column; gap: 2px">
                <Link class="side-link" href="/"><Icon name="house" />الصفحة الرئيسية</Link>
                <Link class="side-link" href="/ask"><Icon name="message-square-text" />صفحة السؤال</Link>
            </nav>
            <div class="sb-foot">
                <div v-if="kb" class="model-pill">
                    <b dir="ltr" style="text-align: right">{{ kb.models.generation }}</b>
                    <span class="muted">الفهرس: {{ kb.documents }} مادة · {{ kb.chunks }} مقطعاً</span>
                    <span v-if="indexedOn" class="muted">فُهرس {{ indexedOn }}</span>
                </div>
                <div v-else class="model-pill">
                    <b>خدمة الإجابة غير متصلة</b><span class="muted">تعذّرت قراءة بيانات النموذج والفهرس.</span>
                </div>
                <div class="who">
                    <span class="avatar">{{ (user?.name || 'م').trim().charAt(0) }}</span>
                    <span class="t">{{ user?.name }}<span>{{ user?.role }}</span></span>
                    <button class="icon-btn" type="button" aria-label="تسجيل الخروج" @click="logout"><Icon name="log-out" flip /></button>
                </div>
            </div>
        </aside>

        <div class="admin-main">
            <header class="admin-top">
                <div class="admin-top-in">
                    <div style="min-width: 0">
                        <h1>{{ title }}</h1>
                        <div class="date num">{{ dateLine }}</div>
                    </div>
                    <span class="grow" />
                    <div v-if="showPeriod" class="seg" role="group" aria-label="الفترة">
                        <button v-for="p in [7, 30, 90]" :key="p" type="button" :aria-pressed="period === p" @click="setPeriod(p)">
                            {{ p === 7 ? '7 أيام' : p === 30 ? '30 يوماً' : '90 يوماً' }}
                        </button>
                    </div>
                    <span v-if="demoBadge" class="badge badge-outline">{{ demoBadge }}</span>
                    <ThemeButton />
                    <button v-if="narrow" class="icon-btn" type="button" aria-label="تسجيل الخروج" @click="logout"><Icon name="log-out" flip /></button>
                </div>
                <nav class="admin-tabs" aria-label="أقسام لوحة الإدارة">
                    <Link v-for="[href, label, icon] in NAV" :key="href" :href="href" :aria-current="path === href ? 'page' : undefined">
                        <Icon :name="icon" size="sm" />{{ label }}<span v-if="href === '/admin/review'" class="num"> {{ pending }}</span>
                    </Link>
                    <Link :href="INBOX[0]" :aria-current="path === INBOX[0] ? 'page' : undefined"><Icon :name="INBOX[2]" size="sm" />{{ INBOX[1] }}<span class="num"> {{ newMessages }}</span></Link>
                    <Link href="/"><Icon name="house" size="sm" />الموقع</Link>
                </nav>
            </header>
            <div id="view" class="admin-content"><slot /></div>
        </div>
    </div>
    <Toasts />
</template>
