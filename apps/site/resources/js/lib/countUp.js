// v-count-up: when a dashboard figure first appears, its number counts up from zero
// (the design's countUps). The text around the number, such as "%" or a unit, stays put.
const DURATION = 1400;
const state = new WeakMap();

const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

function stop(el) {
    const run = state.get(el);
    if (!run) return;
    cancelAnimationFrame(run.frame);
    run.node.nodeValue = run.original;
    state.delete(el);
}

export const countUp = {
    mounted(el) {
        if (reduceMotion()) return;
        const node = [...el.childNodes].find((n) => n.nodeType === 3 && /\d/.test(n.nodeValue));
        const match = node?.nodeValue.match(/[\d,]*\.?\d+/);
        if (!match) return;

        const original = node.nodeValue;
        const raw = match[0];
        const target = parseFloat(raw.replace(/,/g, ''));
        const decimals = (raw.split('.')[1] || '').length;
        const format = (v) =>
            raw.includes(',') ? v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : v.toFixed(decimals);

        const run = { node, original, frame: 0 };
        const started = performance.now();
        const step = (now) => {
            const progress = Math.min(1, (now - started) / DURATION);
            if (progress >= 1) {
                stop(el);
                return;
            }
            node.nodeValue = original.replace(raw, format(target * (1 - Math.pow(1 - progress, 4))));
            run.frame = requestAnimationFrame(step);
        };
        node.nodeValue = original.replace(raw, format(0));
        state.set(el, run);
        run.frame = requestAnimationFrame(step);
    },
    // If the figure changes mid-count, hand the text back to Vue untouched before it patches.
    beforeUpdate: stop,
    beforeUnmount: stop,
};
