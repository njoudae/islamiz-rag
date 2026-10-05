<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Cross-Origin Resource Sharing
    |--------------------------------------------------------------------------
    |
    | The visitor pages are served by this application, so the public API is
    | same-origin and needs no CORS. List extra origins in
    | CORS_ALLOWED_ORIGINS only if another frontend must call it.
    |
    */

    'paths' => ['api/*'],

    'allowed_methods' => ['GET', 'POST', 'OPTIONS'],

    'allowed_origins' => array_values(array_filter(array_map(
        'trim',
        explode(',', (string) env('CORS_ALLOWED_ORIGINS', '')),
    ))),

    'allowed_origins_patterns' => [],

    'allowed_headers' => ['Content-Type', 'Accept', 'X-Requested-With', 'X-Visitor-Id'],

    'exposed_headers' => [],

    'max_age' => 600,

    'supports_credentials' => false,

];
