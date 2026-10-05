<!DOCTYPE html>
<html lang="ar" dir="rtl">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
        <meta name="description" content="أداة تجيب عن الأسئلة الفقهية بالصوت أو النص من الموسوعة الفقهية في الدرر السنية">
        <link rel="icon" href="/favicon.svg" type="image/svg+xml">

        <title inertia>دليل</title>

        {{-- Apply the saved theme before the first paint, so dark mode does not flash. --}}
        <script>
            try {
                const theme = JSON.parse(localStorage.getItem('daleel:theme'));
                if (theme === 'dark' || theme === 'light') document.documentElement.setAttribute('data-theme', theme);
            } catch (e) {}
        </script>

        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@400;500;600;700&family=Tajawal:wght@400;500;700;800&display=swap">

        @vite(['resources/css/app.css', 'resources/js/app.js'])
        @inertiaHead
    </head>
    <body>
        @inertia
        <div class="toasts" id="toasts" aria-live="polite"></div>
        <div class="tip" id="tip" hidden></div>
    </body>
</html>
