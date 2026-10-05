<script setup>
import { computed } from 'vue';

const props = defineProps({
    values: { type: Array, required: true },
    color: { type: String, default: 'var(--foreground)' },
});

const W = 80;
const H = 28;

const shape = computed(() => {
    const vals = props.values.filter((v) => Number.isFinite(v));
    if (!vals.length) return null;
    const mn = Math.min(...vals);
    const rg = Math.max(...vals) - mn || 1;
    const pts = vals.map((v, i) => [(i / (vals.length - 1 || 1)) * (W - 4) + 2, H - 3 - ((v - mn) / rg) * (H - 6)]);
    const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
    const last = pts[pts.length - 1];
    return { d, area: `${d} L${last[0]} ${H} L${pts[0][0]} ${H} Z`, last };
});
</script>

<template>
    <svg v-if="shape" class="spark" :viewBox="`0 0 ${W} ${H}`" aria-hidden="true" style="direction: ltr">
        <path :d="shape.area" :style="{ fill: color, stroke: 'none' }" fill-opacity=".08" />
        <path :d="shape.d" :style="{ fill: 'none', stroke: color }" stroke-opacity=".55" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
        <circle :cx="shape.last[0]" :cy="shape.last[1]" r="2.5" :style="{ fill: color, stroke: 'var(--card)' }" stroke-width="1.5" />
    </svg>
</template>
