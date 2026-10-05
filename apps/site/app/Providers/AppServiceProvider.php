<?php

namespace App\Providers;

use App\Services\Ai\AiClient;
use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        $this->app->singleton(AiClient::class, fn () => new AiClient(
            baseUrl: (string) config('services.ai.base_url'),
            token: config('services.ai.token') ?: null,
            timeout: (int) config('services.ai.timeout'),
            connectTimeout: (int) config('services.ai.connect_timeout'),
        ));
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // Surface N+1 queries, silently dropped attributes and missing attributes during development.
        Model::shouldBeStrict(! $this->app->isProduction());

        RateLimiter::for('ask', fn (Request $request) => Limit::perMinute(
            (int) config('daleel.ask.rate_limit_per_minute'),
        )->by($request->ip()));

        // The contact form: a handful of messages per visitor every ten minutes.
        RateLimiter::for('contact', fn (Request $request) => Limit::perMinutes(10, 5)->by($request->ip()));
    }
}
