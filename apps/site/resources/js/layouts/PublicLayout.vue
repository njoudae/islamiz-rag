<script setup>
import { Link, usePage } from '@inertiajs/vue3';
import { computed, ref, watch } from 'vue';
import Icon from '../components/Icon.vue';
import Logo from '../components/Logo.vue';
import ThemeButton from '../components/ThemeButton.vue';
import Toasts from '../components/Toasts.vue';
import { DORAR } from '../lib/content.js';
import { dHijri } from '../lib/format.js';

const page = usePage();
const path = computed(() => page.url.split('?')[0]);
const isAdmin = computed(() => page.props.auth?.user?.isAdmin === true);
const menuOpen = ref(false);
watch(path, () => (menuOpen.value = false));

const NAV = [
    ['/', 'الرئيسية', 'house'],
    ['/ask', 'اسأل دليل', 'message-square-text'],
    ['/encyclopedia', 'الموسوعة الفقهية', 'library'],
    ['/contact', 'تواصل معنا', 'mail'],
];
const today = dHijri.format(new Date());
</script>

<template>
    <header class="topbar">
        <div class="wrap topbar-in">
            <Link class="brand" href="/" aria-label="دليل، الصفحة الرئيسية"><Logo /><span>دليل</span></Link>
            <nav class="nav" aria-label="التنقل الرئيسي">
                <Link v-for="[href, label] in NAV" :key="href" :href="href" :aria-current="path === href ? 'page' : undefined">{{ label }}</Link>
            </nav>
            <div class="top-actions">
                <ThemeButton />
                <Link v-if="isAdmin" class="btn btn-outline only-desk" href="/admin"><Icon name="layout-dashboard" />لوحة الإدارة</Link>
                <Link v-else class="btn btn-outline only-desk" href="/login"><Icon name="log-in" flip />دخول المشرفين</Link>
                <button class="icon-btn only-mobile" type="button" :aria-expanded="menuOpen" aria-controls="mnav" aria-label="القائمة" @click="menuOpen = !menuOpen">
                    <Icon :name="menuOpen ? 'x' : 'menu'" />
                </button>
            </div>
        </div>
        <div id="mnav" class="wrap mnav" :hidden="!menuOpen">
            <Link v-for="[href, label, icon] in NAV" :key="href" :href="href" :aria-current="path === href ? 'page' : undefined"><Icon :name="icon" />{{ label }}</Link>
            <Link :href="isAdmin ? '/admin' : '/login'"><Icon :name="isAdmin ? 'layout-dashboard' : 'log-in'" :flip="!isAdmin" />{{ isAdmin ? 'لوحة الإدارة' : 'دخول المشرفين' }}</Link>
        </div>
    </header>

    <main id="main"><slot /></main>

    <footer v-if="path !== '/ask'" class="site-foot">
        <div class="wrap foot-in">
            <span>المحتوى العلمي مصدره <a :href="DORAR" target="_blank" rel="noopener">الموسوعة الفقهية في موقع الدرر السنية</a>. دليل أداة بحث تعليمية، وليس جهة إفتاء. <Link href="/contact">تواصل معنا</Link></span>
            <span class="num">{{ today }}</span>
        </div>
    </footer>

    <Toasts />
</template>
