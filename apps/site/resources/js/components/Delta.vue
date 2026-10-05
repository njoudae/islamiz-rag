<script setup>
import { computed } from 'vue';
import Icon from './Icon.vue';

// Change between the current and previous period, coloured by whether up is good.
const props = defineProps({
    cur: { type: Number, default: null },
    prev: { type: Number, default: null },
    pct: { type: Boolean, default: false }, // relative change in percent
    pp: { type: Boolean, default: false }, // difference of two shares, in percentage points
    goodUp: { type: Boolean, default: true },
    neutral: { type: Boolean, default: false },
    unit: { type: String, default: '' },
});

const view = computed(() => {
    const { cur, prev } = props;
    if (!Number.isFinite(cur) || !Number.isFinite(prev)) return null;
    let d;
    let number;
    let rest = '';
    if (props.pp) {
        d = (cur - prev) * 100;
        number = (d > 0 ? '+' : '') + d.toFixed(1);
        rest = 'نقطة';
    } else if (props.pct) {
        d = prev ? ((cur - prev) / prev) * 100 : 0;
        number = (d > 0 ? '+' : '') + d.toFixed(1) + '%';
    } else {
        d = cur - prev;
        number = (d > 0 ? '+' : '') + d.toFixed(1);
        rest = props.unit.trim();
    }
    const flat = Math.abs(d) < 0.05;
    const cls = props.neutral || flat ? 'flat' : d > 0 === props.goodUp ? 'good' : 'bad';
    return { cls, number, rest, icon: props.neutral || flat ? null : d > 0 ? 'trending-up' : 'trending-down' };
});
</script>

<template>
    <span v-if="view" class="delta" :class="view.cls">
        <Icon v-if="view.icon" :name="view.icon" size="xs" /><span class="dn">{{ view.number }}</span><template v-if="view.rest"> {{ view.rest }}</template>
    </span>
    <span v-else class="delta flat">—</span>
</template>
