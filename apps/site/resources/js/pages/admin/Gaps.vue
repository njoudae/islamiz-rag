<script setup>
import { Head, Link, router } from '@inertiajs/vue3';
import Icon from '../../components/Icon.vue';
import StBadge from '../../components/StBadge.vue';
import AdminLayout from '../../layouts/AdminLayout.vue';
import { ratio } from '../../lib/admin.js';
import { fmtN, fmtPct, periodAr } from '../../lib/format.js';

defineOptions({ layout: AdminLayout });

defineProps({
    period: { type: Number, required: true },
    insufficient: { type: Array, required: true }, // gap groups from the real question log
    outOfScope: { type: Array, required: true },
    sections: { type: Array, required: true },
    openTasks: { type: Number, default: 0 },
});

function createTask(group) {
    router.post('/admin/gaps/tasks', { group_key: group.key, kind: group.kind, title: group.title }, { preserveScroll: true });
}

function setTask(group, status) {
    router.patch(`/admin/gaps/tasks/${group.task.id}`, { status }, { preserveScroll: true });
}

const reviewLink = (state, search) => `/admin/review?filter=all&state=${state}${search ? `&search=${encodeURIComponent(search.slice(0, 120))}` : ''}`;
</script>

<template>
    <Head title="فجوات المعرفة" />

    <div class="view-intro">
        <p>
            أسئلة فعلية لم يجد لها النموذج أدلة كافية، أو خرجت عن نطاق الموسوعة الفقهية. الأعداد خلال {{ periodAr(period) }}، والتغيّر مقارنة بالفترة السابقة.
            المهام المفتوحة: <b class="num">{{ fmtN(openTasks) }}</b>.
        </p>
    </div>

    <section class="card">
        <div class="card-head">
            <div>
                <h2 class="card-title" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap"><StBadge state="INSUFFICIENT_EVIDENCE" />موضوعات بلا أدلة كافية</h2>
                <p class="card-desc">مجمّعة حسب الفصل الذي يقع فيه أقرب مقطع مفهرس. ما لا يقاربه أي مقطع يُجمع في «مسائل لا يغطيها الفهرس الحالي».</p>
            </div>
        </div>
        <div v-if="!insufficient.length" class="empty" style="padding: 24px 8px">
            <Icon name="file-search" size="lg" /><b style="color: var(--foreground)">لا أسئلة بلا أدلة خلال الفترة</b>
        </div>
        <div v-else class="gaps">
            <div v-for="g in insufficient" :key="g.key" class="gap-row">
                <div>
                    <h3>{{ g.title }}</h3>
                    <div class="ex"><template v-for="(e, j) in g.examples" :key="j">«{{ e }}»<br v-if="j < g.examples.length - 1" /></template></div>
                </div>
                <div>
                    <div class="cnt">{{ fmtN(g.n) }}</div>
                    <span v-if="g.delta !== null" class="delta" :class="g.delta > 0 ? 'bad' : g.delta < 0 ? 'good' : 'flat'">
                        <Icon v-if="g.delta !== 0" :name="g.delta > 0 ? 'trending-up' : 'trending-down'" size="xs" /><span class="dn">{{ g.delta > 0 ? '+' : '' }}{{ g.delta }}%</span>
                    </span>
                    <span v-else class="delta flat">جديد</span>
                </div>
                <div class="near">
                    <template v-if="g.book"><span>الكتاب: </span>{{ g.book }}</template>
                    <template v-else><span>لا مادة قريبة في الفهرس.</span></template>
                    <div style="margin-top: 4px"><Link class="act-link" :href="reviewLink('INSUFFICIENT_EVIDENCE')">افتح الأسئلة في الطابور<Icon name="arrow-left" size="xs" /></Link></div>
                </div>
                <div>
                    <button v-if="!g.task" class="btn btn-outline btn-sm" type="button" @click="createTask(g)"><Icon name="plus" />أنشئ مهمة</button>
                    <button v-else-if="g.task.status === 'open'" class="btn btn-outline btn-sm" type="button" data-tip="اضغط لإغلاق المهمة" @click="setTask(g, 'done')"><Icon name="clock" />قيد المعالجة</button>
                    <button v-else class="btn btn-ghost btn-sm" type="button" data-tip="اضغط لإعادة فتح المهمة" @click="setTask(g, 'open')"><Icon name="check" />أُنجزت</button>
                </div>
            </div>
        </div>
    </section>

    <section class="card">
        <div class="card-head">
            <div>
                <h2 class="card-title" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap"><StBadge state="OUT_OF_SCOPE" />أسئلة خارج النطاق</h2>
                <p class="card-desc">الأسئلة غير الفقهية، مجمّعة حين يتكرر السؤال نفسه. التكرار يدل على أن الزوار يتوقعون شيئاً لا يقدّمه دليل.</p>
            </div>
        </div>
        <div v-if="!outOfScope.length" class="empty" style="padding: 24px 8px">
            <Icon name="ban" size="lg" /><b style="color: var(--foreground)">لا أسئلة خارج النطاق خلال الفترة</b>
        </div>
        <div v-else class="gaps">
            <div v-for="g in outOfScope" :key="g.key" class="gap-row">
                <div><h3>{{ g.title }}</h3></div>
                <div>
                    <div class="cnt">{{ fmtN(g.n) }}</div>
                    <span v-if="g.delta !== null" class="delta" :class="g.delta > 0 ? 'bad' : g.delta < 0 ? 'good' : 'flat'"><span class="dn">{{ g.delta > 0 ? '+' : '' }}{{ g.delta }}%</span></span>
                    <span v-else class="delta flat">جديد</span>
                </div>
                <div class="near">
                    <Link class="act-link" :href="reviewLink('OUT_OF_SCOPE', g.title)">افتحه في الطابور<Icon name="arrow-left" size="xs" /></Link>
                </div>
                <div>
                    <button v-if="!g.task" class="btn btn-outline btn-sm" type="button" @click="createTask(g)"><Icon name="plus" />أنشئ مهمة</button>
                    <button v-else-if="g.task.status === 'open'" class="btn btn-outline btn-sm" type="button" data-tip="اضغط لإغلاق المهمة" @click="setTask(g, 'done')"><Icon name="clock" />قيد المعالجة</button>
                    <button v-else class="btn btn-ghost btn-sm" type="button" data-tip="اضغط لإعادة فتح المهمة" @click="setTask(g, 'open')"><Icon name="check" />أُنجزت</button>
                </div>
            </div>
        </div>
    </section>

    <section class="card">
        <div>
            <h2 class="card-title">تغطية الفهرس حسب الفصل</h2>
            <p class="card-desc">الفصول الأكثر سؤالاً خلال الفترة. انخفاض الإجابة المباشرة مع ارتفاع «أدلة غير كافية» يعني نقصاً في المادة المفهرسة لذلك الفصل.</p>
        </div>
        <div v-if="!sections.length" class="empty" style="padding: 24px 8px">
            <Icon name="library" size="lg" /><b style="color: var(--foreground)">لا بيانات بعد</b>
            <span style="line-height: 1.7">يظهر الفصل حين تطابق مادة مفهرسة سؤال الزائر.</span>
        </div>
        <div v-else class="table-scroll">
            <table class="vtable">
                <thead><tr><th>الفصل</th><th>الكتاب</th><th>الأسئلة</th><th>إجابة مباشرة</th><th>أدلة غير كافية</th></tr></thead>
                <tbody>
                    <tr v-for="b in sections" :key="b.book + b.chapter">
                        <td>{{ b.chapter }}</td>
                        <td class="muted">{{ b.book }}</td>
                        <td class="n">{{ fmtN(b.total) }}</td>
                        <td>
                            <span class="meter"><span class="meter-track" style="width: 72px"><span class="meter-fill" :style="{ width: ratio(b.answered, b.total) * 100 + '%', background: 'var(--st-ans)' }" /></span><span class="num">{{ fmtPct(ratio(b.answered, b.total), 0) }}</span></span>
                        </td>
                        <td>
                            <span class="meter"><span class="meter-track" style="width: 72px"><span class="meter-fill" :style="{ width: ratio(b.insufficient, b.total) * 100 + '%', background: 'var(--st-insuf)' }" /></span><span class="num">{{ fmtPct(ratio(b.insufficient, b.total), 0) }}</span></span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>
</template>
