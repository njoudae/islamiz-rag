<script setup>
import Icon from './Icon.vue';
import { STATUS } from '../lib/content.js';

defineProps({
    state: { type: String, required: true },
    code: { type: Boolean, default: false },
});
</script>

<template>
    <span class="st" :data-st="state">
        <Icon :name="STATUS[state]?.icon || 'info'" />{{ STATUS[state]?.ar || state }}
        <span v-if="code" class="latin">{{ state }}</span>
    </span>
</template>
