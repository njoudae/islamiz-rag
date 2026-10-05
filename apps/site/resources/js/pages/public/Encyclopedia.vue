<script setup>
import { Head, Link, router } from '@inertiajs/vue3';
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import Icon from '../../components/Icon.vue';
import PublicLayout from '../../layouts/PublicLayout.vue';
import { BOOKS, BOOK_GROUPS, DORAR } from '../../lib/content.js';
import { booksAr, fmtN, norm } from '../../lib/format.js';

defineOptions({ layout: PublicLayout });

const initialGroup = new URLSearchParams(window.location.search).get('group');
const group = ref(BOOK_GROUPS.some((g) => g.id === initialGroup) ? initialGroup : 'all');
const search = ref('');

const tabs = [['all', 'الكل', BOOKS.length], ...BOOK_GROUPS.map((g) => [g.id, g.name, g.books.length])];
const totalChapters = BOOKS.reduce((n, b) => n + b.chapters.length, 0);
const totalEntries = BOOKS.reduce((n, b) => n + b.entries, 0);

const chaptersAr = (n) => (n === 1 ? 'باب واحد' : n === 2 ? 'بابان' : n <= 10 ? `${n} أبواب` : `${n} باباً`);
const entriesAr = (n) => (n === 1 ? 'مسألة واحدة' : n === 2 ? 'مسألتان' : n <= 10 ? `${fmtN(n)} مسائل` : `${fmtN(n)} مسألة`);

// A search matches a book by its title or by the title of any of its chapters.
const groups = computed(() => {
    const qn = norm(search.value);
    const matches = (b) => !qn || norm(b.title).includes(qn) || b.chapters.some((c) => norm(c.title).includes(qn));
    return BOOK_GROUPS.filter((g) => group.value === 'all' || g.id === group.value)
        .map((g) => ({ ...g, list: BOOKS.filter((b) => b.group === g.id && matches(b)) }))
        .filter((g) => g.list.length);
});
const matchedChapter = (b) => {
    const qn = norm(search.value);
    return qn && !norm(b.title).includes(qn) ? b.chapters.find((c) => norm(c.title).includes(qn)) : null;
};

// Picking a group in the banner filters the list and brings it into view.
const listTop = ref(null);
function showGroup(id) {
    group.value = id;
    search.value = '';
    nextTick(() => listTop.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
}

function askAbout(book) {
    router.visit(`/ask?prefill=${encodeURIComponent(`سؤالي في ${book}: `)}`);
}

/* ---------- Chapters sheet ---------- */
const open = ref(null);
const closeButton = ref(null);
let opener = null;

function openBook(book, event) {
    opener = event?.currentTarget ?? null;
    open.value = book;
    nextTick(() => closeButton.value?.focus());
}

function closeSheet() {
    open.value = null;
    opener?.focus();
}

const onKey = (e) => {
    if (e.key === 'Escape' && open.value) closeSheet();
};
onMounted(() => window.addEventListener('keydown', onKey));
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));
</script>

<template>
    <Head title="الموسوعة الفقهية" />

    <div class="wrap">
        <div class="enc-head">
            <div style="display: flex; flex-direction: column; gap: 12px; min-width: 0">
                <span class="eyebrow"><Icon name="library" />المصدر العلمي لدليل</span>
                <h1 class="h1" style="font-size: clamp(1.75rem, 1.3rem + 2vw, 2.5rem)">الموسوعة الفقهية – الدرر السنية</h1>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap">
                <a class="btn" :href="DORAR" target="_blank" rel="noopener">افتح الموسوعة<Icon name="external-link" size="sm" /></a>
                <Link class="btn btn-outline" href="/ask">اسأل دليل</Link>
            </div>
        </div>

        <section class="featured" style="margin-top: 24px" aria-labelledby="ft">
            <div style="display: flex; flex-direction: column; gap: 12px">
                <span class="badge badge-dark" style="align-self: flex-start">فهرس الموسوعة</span>
                <h2 id="ft" class="h2">{{ BOOKS.length }} كتاباً في سبعة أبواب كبرى</h2>
                <p class="muted" style="line-height: 1.8">
                    {{ fmtN(totalChapters) }} باباً وأكثر من {{ fmtN(Math.floor(totalEntries / 100) * 100) }} مسألة، من الطهارة إلى الجهاد. اختر باباً لعرض كتبه.
                </p>
                <div style="display: flex; gap: 8px; flex-wrap: wrap">
                    <Link class="btn btn-outline btn-sm" href="/ask"><Icon name="message-square-text" />اسأل دليل</Link>
                    <a class="btn btn-ghost btn-sm" :href="DORAR" target="_blank" rel="noopener">في الدرر السنية<Icon name="external-link" size="sm" /></a>
                </div>
            </div>
            <ol class="chapters" aria-label="الأبواب الكبرى">
                <li v-for="(g, i) in BOOK_GROUPS" :key="g.id">
                    <span class="n">{{ i + 1 }}</span>
                    <button class="chapter-link group-link" type="button" :aria-pressed="group === g.id" @click="showGroup(g.id)">{{ g.name }}</button>
                    <span class="muted num" style="margin-inline-start: auto; font-size: 0.75rem; white-space: nowrap">{{ booksAr(g.books.length) }}</span>
                </li>
            </ol>
        </section>

        <div ref="listTop" class="enc-tools">
            <div class="search">
                <label class="sr-only" for="encQ">ابحث في الكتب والأبواب</label><Icon name="search" />
                <input id="encQ" v-model="search" class="input" placeholder="ابحث باسم كتاب أو باب، مثل: الزكاة" />
            </div>
            <div class="tabs" role="tablist" aria-label="أبواب الموسوعة">
                <button v-for="[id, name, count] in tabs" :key="id" class="tab" role="tab" type="button" :aria-selected="group === id" @click="group = id">
                    {{ name }}<span class="count">{{ count }}</span>
                </button>
            </div>
        </div>

        <div style="padding-bottom: 48px">
            <template v-for="g in groups" :key="g.id">
                <div class="group-title">
                    <h2>{{ g.name }}</h2>
                    <span class="muted num">{{ booksAr(g.list.length) }}</span>
                    <span class="muted" style="font-size: 0.8125rem">· {{ g.note }}</span>
                </div>
                <div class="books">
                    <article v-for="b in g.list" :key="b.no" class="book">
                        <div class="top">
                            <span class="no">الكتاب {{ b.no }}</span><span class="badge">{{ chaptersAr(b.chapters.length) }}</span>
                        </div>
                        <h3><a class="chapter-link" :href="b.url" target="_blank" rel="noopener">{{ b.title }}</a></h3>
                        <p class="help num" style="line-height: 1.7">{{ entriesAr(b.entries) }}</p>
                        <p v-if="matchedChapter(b)" class="help" style="line-height: 1.7">فيه: {{ matchedChapter(b).title }}</p>
                        <div class="acts">
                            <button class="btn btn-outline btn-xs" type="button" @click="openBook(b, $event)"><Icon name="list-checks" size="xs" />الأبواب</button>
                            <button class="btn btn-ghost btn-xs" type="button" @click="askAbout(b.title)"><Icon name="message-square-text" size="xs" />اسأل عنه</button>
                            <a class="btn btn-ghost btn-xs" :href="b.url" target="_blank" rel="noopener" :aria-label="`${b.title} في الدرر السنية`">في الدرر<Icon name="external-link" size="xs" /></a>
                        </div>
                    </article>
                </div>
            </template>
            <div v-if="!groups.length" class="empty">
                <Icon name="search" size="lg" /><b style="color: var(--foreground)">لا يوجد كتاب أو باب بهذا الاسم</b><span>ابحث بكلمة أخرى، مثل «البيع» أو «النكاح».</span>
            </div>
        </div>
    </div>

    <template v-if="open">
        <div class="overlay" @click="closeSheet" />
        <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="book-t">
            <div class="sheet-head">
                <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px">
                    <h2 id="book-t">{{ open.title }}</h2>
                    <div class="muted num" style="font-size: 0.8125rem">الكتاب {{ open.no }} · {{ chaptersAr(open.chapters.length) }} · {{ entriesAr(open.entries) }}</div>
                </div>
                <button ref="closeButton" class="icon-btn" type="button" aria-label="إغلاق" @click="closeSheet"><Icon name="x" /></button>
            </div>
            <div class="sheet-body">
                <ol class="chapters chapters-list" :aria-label="`أبواب ${open.title}`">
                    <li v-for="(c, i) in open.chapters" :key="c.url">
                        <span class="n">{{ i + 1 }}</span>
                        <a class="chapter-link" :href="c.url" target="_blank" rel="noopener">{{ c.title }}</a>
                        <span class="muted num" style="margin-inline-start: auto; font-size: 0.75rem; white-space: nowrap">{{ entriesAr(c.entries) }}</span>
                    </li>
                </ol>
                <p class="help" style="line-height: 1.7">كل باب يفتح أول مسائله في موقع الدرر السنية.</p>
            </div>
            <div class="sheet-foot">
                <a class="btn" :href="open.url" target="_blank" rel="noopener">افتح الكتاب في الدرر<Icon name="external-link" size="sm" /></a>
                <button class="btn btn-outline" type="button" @click="askAbout(open.title)"><Icon name="message-square-text" />اسأل عنه</button>
            </div>
        </aside>
    </template>
</template>
