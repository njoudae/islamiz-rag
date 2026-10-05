<script setup>
import { Head, Link, router } from '@inertiajs/vue3';
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import Icon from '../../components/Icon.vue';
import AdminLayout from '../../layouts/AdminLayout.vue';
import { agoAr, dLong, fmtN, minutesSince } from '../../lib/format.js';

defineOptions({ layout: AdminLayout });

const props = defineProps({
    messages: { type: Object, required: true }, // paginated: { data, links, current_page, last_page, total, ... }
    filters: { type: Object, required: true },
    counts: { type: Object, required: true },
});

const f = reactive({ status: props.filters.status, search: props.filters.search ?? '' });

function apply() {
    router.get('/admin/messages', { status: f.status, search: f.search || undefined }, { preserveState: true, preserveScroll: true, replace: true });
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
    f.status = id;
    apply();
}

/* ---------- Message sheet ---------- */
const open = ref(null);

function setStatus(message, status, opts = {}) {
    router.patch(`/admin/messages/${message.id}`, { status }, { preserveScroll: true, preserveState: true, ...opts });
}

function openMessage(m) {
    open.value = { ...m };
    // Opening a new message marks it as read.
    if (m.status === 'new') {
        open.value.status = 'read';
        setStatus(m, 'read');
    }
}

function closeSheet() {
    open.value = null;
}

function archive(m) {
    setStatus(m, 'archived', { onSuccess: closeSheet });
}

function restore(m) {
    setStatus(m, 'read', { onSuccess: closeSheet });
}

function markUnread(m) {
    setStatus(m, 'new', { onSuccess: closeSheet });
}

const onKey = (e) => {
    if (e.key === 'Escape' && open.value) closeSheet();
};
onMounted(() => window.addEventListener('keydown', onKey));
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));

const tabs = [
    ['new', 'جديدة'],
    ['read', 'مقروءة'],
    ['archived', 'مؤرشفة'],
    ['all', 'الكل'],
];
const statusLabel = { new: 'جديدة', read: 'مقروءة', archived: 'مؤرشفة' };
const mailto = (m) => `mailto:${m.email}?subject=${encodeURIComponent('رد من فريق دليل: ' + m.topic_label)}`;
</script>

<template>
    <Head title="رسائل التواصل" />

    <div class="view-intro">
        <p>ما يرسله الزوار من صفحة «تواصل معنا». الرسالة الجديدة تصبح مقروءة عند فتحها، ويمكن أرشفتها بعد التعامل معها أو الرد عليها بالبريد.</p>
    </div>

    <div class="kpis" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))">
        <div class="card kpi"><span class="lbl"><Icon name="mail" size="sm" />رسائل جديدة</span><span class="val">{{ fmtN(counts.new) }}</span></div>
        <div class="card kpi"><span class="lbl"><Icon name="check" size="sm" />مقروءة</span><span class="val">{{ fmtN(counts.read) }}</span></div>
        <div class="card kpi"><span class="lbl"><Icon name="inbox" size="sm" />مؤرشفة</span><span class="val">{{ fmtN(counts.archived) }}</span></div>
    </div>

    <section class="card">
        <div class="q-tools">
            <div class="tabs" role="tablist">
                <button v-for="[id, label] in tabs" :key="id" class="tab" type="button" role="tab" :aria-selected="f.status === id" @click="setTab(id)">
                    {{ label }}<span class="count">{{ counts[id] }}</span>
                </button>
            </div>
            <div class="search">
                <label class="sr-only" for="mSearch">ابحث في الرسائل</label><Icon name="search" />
                <input id="mSearch" v-model="f.search" class="input" placeholder="ابحث بالاسم أو البريد أو نص الرسالة" />
            </div>
        </div>

        <div v-if="!messages.data.length" class="empty">
            <Icon name="mail" size="lg" /><b style="color: var(--foreground)">لا توجد رسائل هنا</b><span>ستظهر رسائل الزوار فور إرسالها من صفحة «تواصل معنا».</span>
        </div>
        <div v-else class="table-scroll">
            <table class="qtable">
                <thead>
                    <tr><th>المرسِل</th><th>الموضوع</th><th>الرسالة</th><th>الوقت</th><th /></tr>
                </thead>
                <tbody>
                    <tr v-for="m in messages.data" :key="m.id" tabindex="0" @click="openMessage(m)" @keydown.enter.prevent="openMessage(m)" @keydown.space.prevent="openMessage(m)">
                        <td style="white-space: nowrap">
                            <div :style="{ fontWeight: m.status === 'new' ? 700 : 500 }">{{ m.name }}</div>
                            <div class="sub" dir="ltr" style="text-align: right">{{ m.email }}</div>
                        </td>
                        <td><span class="badge">{{ m.topic_label }}</span></td>
                        <td class="c-q"><div class="qtext" :style="{ fontWeight: m.status === 'new' ? 600 : 400 }">{{ m.message }}</div></td>
                        <td class="c-hide" style="white-space: nowrap; color: var(--muted-foreground)">{{ agoAr(minutesSince(m.created_at)) }}</td>
                        <td>
                            <span v-if="m.status === 'new'" class="badge badge-dark">جديدة</span>
                            <span v-else class="muted" style="font-size: 0.8125rem">{{ statusLabel[m.status] }}</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <nav v-if="messages.last_page > 1" class="pager" aria-label="ترقيم الصفحات">
            <component :is="messages.prev_page_url ? Link : 'span'" :href="messages.prev_page_url" preserve-scroll class="btn btn-outline btn-sm" :style="messages.prev_page_url ? '' : 'opacity:.4'">السابق</component>
            <span class="num">صفحة {{ messages.current_page }} من {{ messages.last_page }} · {{ fmtN(messages.total) }} رسالة</span>
            <component :is="messages.next_page_url ? Link : 'span'" :href="messages.next_page_url" preserve-scroll class="btn btn-outline btn-sm" :style="messages.next_page_url ? '' : 'opacity:.4'">التالي</component>
        </nav>
    </section>

    <template v-if="open">
        <div class="overlay" @click="closeSheet" />
        <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="msg-t">
            <div class="sheet-head">
                <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px">
                    <h2 id="msg-t">رسالة من {{ open.name }}</h2>
                    <div><span class="badge">{{ open.topic_label }}</span></div>
                </div>
                <button class="icon-btn" type="button" aria-label="إغلاق" @click="closeSheet"><Icon name="x" /></button>
            </div>
            <div class="sheet-body">
                <dl class="kv">
                    <dt>الاسم</dt><dd>{{ open.name }}</dd>
                    <dt>البريد</dt><dd dir="ltr" style="text-align: right"><a :href="`mailto:${open.email}`">{{ open.email }}</a></dd>
                    <dt>الموضوع</dt><dd>{{ open.topic_label }}</dd>
                    <dt>وصلت</dt><dd>{{ dLong.format(new Date(open.created_at)) }} · {{ agoAr(minutesSince(open.created_at)) }}</dd>
                    <dt>الحالة</dt><dd>{{ statusLabel[open.status] }}</dd>
                    <dt>نسخة للمرسِل</dt><dd>{{ open.send_copy ? 'طلب نسخة على بريده' : 'لا' }}</dd>
                </dl>
                <div v-if="open.related_question" class="evid">
                    <span class="ans-label"><Icon name="message-square-text" size="sm" />السؤال الذي سأله في دليل</span>
                    <div class="quote para">{{ open.related_question }}</div>
                    <Link class="act-link" :href="`/admin/review?filter=all&search=${encodeURIComponent(open.related_question.slice(0, 120))}`">ابحث عنه في طابور المراجعة<Icon name="arrow-left" size="xs" /></Link>
                </div>
                <hr class="separator" />
                <div class="msg-body">{{ open.message }}</div>
            </div>
            <div class="sheet-foot">
                <a class="btn" :href="mailto(open)"><Icon name="mail" />الرد بالبريد</a>
                <button v-if="open.status !== 'archived'" class="btn btn-outline" type="button" @click="archive(open)"><Icon name="inbox" />أرشفة</button>
                <button v-else class="btn btn-outline" type="button" @click="restore(open)"><Icon name="refresh-cw" />إلغاء الأرشفة</button>
                <button v-if="open.status === 'read'" class="btn btn-ghost" type="button" @click="markUnread(open)">وضعها كغير مقروءة</button>
            </div>
        </aside>
    </template>
</template>
