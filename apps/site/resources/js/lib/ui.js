// Small pieces of shared UI state: theme, toasts and the hover tooltip.
import { reactive, ref } from 'vue';

/* ---------- Theme ---------- */
const THEME_KEY = 'daleel:theme';

function systemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function readTheme() {
    const t = document.documentElement.getAttribute('data-theme');
    return t === 'dark' || t === 'light' ? t : systemTheme();
}

export const theme = ref(typeof document === 'undefined' ? 'light' : readTheme());

export function toggleTheme() {
    const next = theme.value === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
        localStorage.setItem(THEME_KEY, JSON.stringify(next));
    } catch {
        // Private mode or blocked storage: the choice simply isn't remembered.
    }
    theme.value = next;
}

/* ---------- Toasts ---------- */
export const toasts = reactive([]);
let toastId = 0;

export function toast(message, icon = 'check') {
    const id = ++toastId;
    toasts.push({ id, message, icon });
    setTimeout(() => {
        const i = toasts.findIndex((t) => t.id === id);
        if (i >= 0) toasts.splice(i, 1);
    }, 3600);
}

/* ---------- Tooltip ----------
 * Any element with data-tip="<b>html</b>" shows a tooltip that follows the pointer.
 * Callers escape dynamic text with esc() before putting it in data-tip. */
export function installTooltip() {
    const tip = document.getElementById('tip');
    if (!tip) return;

    window.showTip = (html, x, y) => {
        tip.innerHTML = html;
        tip.hidden = false;
        const r = tip.getBoundingClientRect();
        let left = x + 14;
        let top = y + 14;
        if (left + r.width > innerWidth - 8) left = x - r.width - 14;
        if (top + r.height > innerHeight - 8) top = y - r.height - 14;
        tip.style.left = Math.max(8, left) + 'px';
        tip.style.top = Math.max(8, top) + 'px';
    };
    window.hideTip = () => {
        tip.hidden = true;
    };

    document.addEventListener('pointermove', (e) => {
        const el = e.target.closest && e.target.closest('[data-tip]');
        if (el) window.showTip(el.getAttribute('data-tip'), e.clientX, e.clientY);
        else if (!e.target.closest || !e.target.closest('.chart-box')) window.hideTip();
    });
}

export const showTip = (html, x, y) => window.showTip?.(html, x, y);
export const hideTip = () => window.hideTip?.();
