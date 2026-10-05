<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Seeded administrator
    |--------------------------------------------------------------------------
    |
    | Ordinary visitors never log in. This single account is created (and kept
    | in sync with these values) by AdminUserSeeder on every container start.
    |
    */

    'admin' => [
        'name' => env('ADMIN_NAME', 'مشرف دليل'),
        'role' => env('ADMIN_ROLE', 'مشرف المحتوى'),
        'email' => env('ADMIN_EMAIL', 'admin@daleel.sa'),
        'password' => env('ADMIN_PASSWORD', 'daleel-admin-2026'),

        // Shows the dummy credentials on the login page, with a "fill" button. Turn off for a real deployment.
        'show_credentials' => (bool) env('ADMIN_SHOW_CREDENTIALS', true),
    ],

    /*
    |--------------------------------------------------------------------------
    | Contact page
    |--------------------------------------------------------------------------
    |
    | The address shown on the contact page for long messages and attachments.
    | Set CONTACT_EMAIL to the mailbox the team reads.
    |
    */

    'contact_email' => env('CONTACT_EMAIL', 'contact@daleel.sa'),

    /*
    |--------------------------------------------------------------------------
    | Public question endpoint
    |--------------------------------------------------------------------------
    */

    'ask' => [
        'rate_limit_per_minute' => (int) env('ASK_RATE_LIMIT_PER_MINUTE', 20),
    ],

];
