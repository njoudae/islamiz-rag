<script setup>
import Icon from './Icon.vue';
import { theme, toggleTheme } from '../lib/ui.js';
</script>

<template>
    <button class="icon-btn" type="button" aria-label="تبديل المظهر" @click="toggleTheme">
        <Icon :name="theme === 'dark' ? 'sun' : 'moon'" />
    </button>
</template>
