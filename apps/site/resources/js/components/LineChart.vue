<script setup>
// The design's daily trend chart: SVG line with a crosshair tooltip.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { clamp, dShort, esc } from '../lib/format.js';
import { hideTip, showTip } from '../lib/ui.js';

const props = defineProps({
    values: { type: Array, required: true },
    dates: { type: Array, required: true }, // Date objects
    format: { type: Function, required: true },
    color: { type: String, required: true },
    name: { type: String, required: true },
    annotations: { type: Array, default: () => [] }, // [{ i, label }]
});

const box = ref(null);
const width = ref(600);
const hover = ref(null);
const H = 252;
const m = { t: 36, r: 14, b: 28, l: 46 };

let observer;
onMounted(() => {
    observer = new ResizeObserver(([entry]) => {
        width.value = Math.max(280, entry.contentRect.width);
    });
    observer.observe(box.value);
});
onBeforeUnmount(() => observer?.disconnect());

function niceStep(max, n = 4) {
    const raw = max / n;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}

const chart = computed(() => {
    const W = width.value;
    const vals = props.values;
    const iw = W - m.l - m.r;
    const ih = H - m.t - m.b;
    const mxv = Math.max(...vals, 0) || 1;
    const step = niceStep(mxv * 1.1);
    const top = Math.ceil((mxv * 1.1) / step) * step;
    const x = (i) => m.l + (vals.length < 2 ? iw / 2 : (i * iw) / (vals.length - 1));
    const y = (v) => m.t + ih - (v / top) * ih;

    const grid = [];
    for (let v = 0; v <= top + 1e-9; v += step) grid.push({ y: y(v), label: props.format(v) });

    const nx = Math.min(W < 520 ? 3 : 5, vals.length);
    const ticks = [];
    for (let k = 0; k < nx; k++) {
        const i = Math.round((k * (vals.length - 1)) / (nx - 1 || 1));
        ticks.push({ x: x(i), label: dShort.format(props.dates[i]), anchor: k === 0 ? 'start' : k === nx - 1 ? 'end' : 'middle' });
    }

    const pts = vals.map((v, i) => [x(i), y(v)]);
    const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
    const last = pts[pts.length - 1];
    const ann = props.annotations.map((a, k) => ({ x: x(a.i), ly: m.t - 22 + (k % 2) * 13, label: a.label }));

    return { W, iw, ih, x, y, grid, ticks, d, area: `${d} L${last[0]} ${m.t + ih} L${pts[0][0]} ${m.t + ih} Z`, last, ann };
});

function move(e) {
    const c = chart.value;
    const r = e.currentTarget.ownerSVGElement.getBoundingClientRect();
    const i = clamp(Math.round(((e.clientX - r.left - m.l) / c.iw) * (props.values.length - 1)), 0, props.values.length - 1);
    hover.value = i;
    const a = props.annotations.find((z) => z.i === i);
    showTip(
        `<div class="tr"><b>${dShort.format(props.dates[i])}</b></div><div class="tr"><span>${esc(props.name)}</span><b class="num">${esc(props.format(props.values[i]))}</b></div>${a ? `<div>${esc(a.label)}</div>` : ''}`,
        e.clientX,
        e.clientY,
    );
}

function leave() {
    hover.value = null;
    hideTip();
}
</script>

<template>
    <div ref="box" class="chart-box">
        <svg :width="chart.W" :height="H" :viewBox="`0 0 ${chart.W} ${H}`" role="img" :aria-label="`${name} يومياً`" style="direction: ltr; display: block">
            <g v-for="g in chart.grid" :key="'g' + g.y">
                <line :x1="m.l" :x2="chart.W - m.r" :y1="g.y" :y2="g.y" style="stroke: var(--border)" stroke-width="1" />
                <text :x="m.l - 8" :y="g.y + 4" text-anchor="end">{{ g.label }}</text>
            </g>
            <text v-for="t in chart.ticks" :key="'t' + t.x" :x="t.x" :y="H - 8" :text-anchor="t.anchor">{{ t.label }}</text>
            <g v-for="a in chart.ann" :key="'a' + a.x">
                <line :x1="a.x" :x2="a.x" :y1="a.ly + 3" :y2="m.t + chart.ih" style="stroke: var(--foreground)" stroke-opacity=".35" stroke-width="1" />
                <text :x="a.x - 4" :y="a.ly" text-anchor="end" style="fill: var(--foreground); font-size: 11px">{{ a.label }}</text>
            </g>
            <path class="area-fade" :d="chart.area" :style="{ fill: color }" fill-opacity=".1" />
            <path class="line-draw" pathLength="1" :d="chart.d" :style="{ fill: 'none', stroke: color }" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
            <circle class="end-dot" :cx="chart.last[0]" :cy="chart.last[1]" r="4" :style="{ fill: color, stroke: 'var(--card)' }" stroke-width="2" />
            <template v-if="hover !== null">
                <line :x1="chart.x(hover)" :x2="chart.x(hover)" :y1="m.t" :y2="m.t + chart.ih" style="stroke: var(--foreground)" stroke-opacity=".4" stroke-width="1" />
                <circle :cx="chart.x(hover)" :cy="chart.y(values[hover])" r="4.5" :style="{ fill: color, stroke: 'var(--card)' }" stroke-width="2" />
            </template>
            <rect :x="m.l" :y="m.t" :width="chart.iw" :height="chart.ih" fill="transparent" @pointermove="move" @pointerleave="leave" />
        </svg>
    </div>
</template>
