import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import { installTooltip } from './lib/ui.js';

const pages = import.meta.glob('./pages/**/*.vue');

createInertiaApp({
    title: (title) => (title ? `${title} · دليل` : 'دليل'),
    resolve: (name) => {
        const page = pages[`./pages/${name}.vue`];

        if (!page) {
            throw new Error(`Inertia page not found: ${name}`);
        }

        return page();
    },
    setup({ el, App, props, plugin }) {
        createApp({ render: () => h(App, props) })
            .use(plugin)
            .mount(el);
        installTooltip();
    },
    progress: { color: 'currentColor' },
});
