<script setup>
import { Head, Link } from '@inertiajs/vue3';
import AnswerCard from '../../components/AnswerCard.vue';
import Icon from '../../components/Icon.vue';
import StBadge from '../../components/StBadge.vue';
import PublicLayout from '../../layouts/PublicLayout.vue';
import { BOOK_GROUPS, DORAR, KB, STATUS, ST_PUBLIC } from '../../lib/content.js';
import { ORN } from '../../lib/icons.js';

defineOptions({ layout: PublicLayout });

// A prepared example answer, shown as it would appear on the ask page.
const sample = { ...KB.wudu_wind, latency: 2.4, mode: 'example', ch: 'voice' };
</script>

<template>
    <Head title="الرئيسية" />

    <section class="hero">
        <div class="hero-orn" aria-hidden="true" v-html="ORN" />
        <div class="wrap hero-grid">
            <div class="hero-copy">
                <span class="eyebrow"><Icon name="book-open" />مبني على الموسوعة الفقهية في الدرر السنية</span>
                <h1 class="h1">اسأل عن مسألتك الفقهية، <span class="grad-text">بصوتك أو بالكتابة</span></h1>
                <p class="lead">يجيبك دليل من الموسوعة الفقهية، ويذكر الدليل والمصدر لكل إجابة، ويقول لك بوضوح متى يحتاج سؤالك إلى مفتٍ.</p>
                <div class="hero-cta">
                    <Link class="btn btn-lg" href="/ask">اسأل دليل الآن<Icon name="arrow-left" /></Link>
                </div>
                <div class="trust">
                    <span><Icon name="quote" />كل إجابة بدليلها</span><span><Icon name="book-marked" />رابط الباب في الموسوعة</span><span><Icon name="scale" />إحالة المسائل الشخصية</span>
                </div>
            </div>
            <div class="hero-stage" aria-label="مثال لإجابة">
                <div class="turn" style="gap: 12px">
                    <div class="qa-user">
                        هل ينقض خروج الريح الوضوء؟
                        <div class="meta"><Icon name="mic" size="xs" />سؤال صوتي، فُرّغ إلى نص</div>
                    </div>
                    <AnswerCard :m="sample" static />
                </div>
            </div>
        </div>
    </section>

    <section class="section" style="padding-top: 24px">
        <div class="wrap">
            <div class="sec-head reveal">
                <h2 class="h2">كيف يعمل دليل</h2>
                <p class="muted" style="line-height: 1.8">ثلاث خطوات من السؤال إلى الإجابة. لا يجيب دليل من عنده، بل مما يجده في الموسوعة.</p>
            </div>
            <div class="steps">
                <div class="step reveal"><span class="step-n">الخطوة 1</span><h3>اسأل بصوتك أو بالكتابة</h3><p>تحدّث كما تسأل شيخاً، أو اكتب سؤالك. يُفرَّغ الصوت إلى نص تراه قبل الإجابة.</p></div>
                <div class="step reveal"><span class="step-n">الخطوة 2</span><h3>يبحث في الموسوعة الفقهية</h3><p>يجمع المسائل المتعلقة بسؤالك من كتب الموسوعة وأبوابها، مع أدلتها من الكتاب والسنة.</p></div>
                <div class="step reveal"><span class="step-n">الخطوة 3</span><h3>يجيب أو يصنّف سؤالك</h3><p>إن وجد الحكم أجابك بدليله ومصدره، وإن لم يجد أخبرك بالسبب وبالخطوة التالية.</p></div>
            </div>
        </div>
    </section>

    <section class="section" style="padding-top: 0">
        <div class="wrap hero-grid" style="align-items: start">
            <div class="sec-head reveal" style="margin: 0">
                <span class="eyebrow"><Icon name="library" />المصدر العلمي</span>
                <h2 class="h2">52 كتاباً من الموسوعة الفقهية</h2>
                <p class="muted" style="line-height: 1.8">أعدّها موقع الدرر السنية، وتبدأ بكتاب الطهارة وتنتهي بكتاب الجهاد. جمعناها هنا في سبعة أبواب كبرى لتسهيل التصفح.</p>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px">
                    <Link class="btn btn-outline" href="/encyclopedia">تصفّح الكتب</Link>
                    <a class="btn btn-ghost" :href="DORAR" target="_blank" rel="noopener">الموسوعة في الدرر السنية<Icon name="external-link" size="sm" /></a>
                </div>
            </div>
            <div class="cats">
                <Link v-for="g in BOOK_GROUPS" :key="g.id" class="cat-row" :href="`/encyclopedia?group=${g.id}`">
                    <span class="n">{{ g.books.length }}</span>
                    <span>
                        <span class="cat-name">{{ g.name }}</span>
                        <span class="cat-books" style="display: block">{{ g.books.slice(0, 4).map((b) => b.replace('كتاب ', '')).join('، ') }}{{ g.books.length > 4 ? '، وغيرها' : '' }}</span>
                    </span>
                    <Icon name="chevron-left" />
                </Link>
            </div>
        </div>
    </section>

    <section class="section">
        <div class="wrap">
            <div class="sec-head reveal">
                <h2 class="h2">ست نتائج ممكنة، وكلها واضحة</h2>
                <p class="muted" style="line-height: 1.8">لا يتظاهر دليل بالمعرفة. يصنّف كل سؤال في واحدة من هذه النتائج، ويخبرك بها في رأس الإجابة.</p>
            </div>
            <div class="outcomes">
                <div v-for="s in ST_PUBLIC" :key="s" class="outcome reveal" :data-st="s">
                    <div><StBadge :state="s" /></div>
                    <p>{{ STATUS[s].pub }}</p>
                    <div class="gets"><Icon name="arrow-left" /><span>{{ STATUS[s].gets }}</span></div>
                </div>
                <div class="outcome wide" style="grid-column: 1 / -1">
                    <p style="color: var(--foreground)">اطرح سؤالك، وستعرف نتيجته في رأس الإجابة.</p>
                    <div><Link class="btn" href="/ask">اسأل دليل<Icon name="arrow-left" /></Link></div>
                </div>
            </div>
        </div>
    </section>

    <section class="section-tight">
        <div class="wrap">
            <div class="notice">
                <Icon name="info" size="lg" />
                <div>
                    <h2 class="h3" style="margin-bottom: 6px">دليل أداة للبحث والتعلّم، وليس مفتياً</h2>
                    <p>في المسائل الشخصية والنوازل، ارجع إلى أهل العلم أو إلى الرئاسة العامة للبحوث العلمية والإفتاء. ولا تعتمد على إجابة لا تذكر دليلها ومصدرها.</p>
                </div>
                <Link class="btn btn-lg" href="/ask">اسأل دليل</Link>
            </div>
        </div>
    </section>
</template>
