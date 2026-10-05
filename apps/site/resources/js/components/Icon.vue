<script setup>
import { ICONS } from '../lib/icons.js';

defineProps({
    name: { type: String, required: true },
    size: { type: String, default: '' }, // '', 'sm', 'xs' or 'lg'
    flip: { type: Boolean, default: false },
});
</script>

<template>
    <svg
        class="i"
        :class="[size ? `i-${size}` : '', { flip }]"
        viewBox="0 0 24 24"
        aria-hidden="true"
        v-html="ICONS[name] || ''"
    />
</template>
