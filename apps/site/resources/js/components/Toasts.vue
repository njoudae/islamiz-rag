<script setup>
import { usePage } from '@inertiajs/vue3';
import { watch } from 'vue';
import Icon from './Icon.vue';
import { toast, toasts } from '../lib/ui.js';

// Server-side flash messages ("saved", "logged out") arrive as a page prop.
const page = usePage();
// Each response carries a new flash object, so the same message twice in a row still shows twice.
watch(
    () => page.props.flash,
    (flash) => {
        if (flash?.toast) toast(flash.toast);
    },
    { immediate: true },
);
</script>

<template>
    <Teleport to="#toasts">
        <div v-for="t in toasts" :key="t.id" class="toast" role="status">
            <Icon :name="t.icon" /><span>{{ t.message }}</span>
        </div>
    </Teleport>
</template>
