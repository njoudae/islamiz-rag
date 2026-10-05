<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Services\Ai\AiClient;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Cache;

/**
 * Whether live answers are available, for the "try" page's mode badge.
 */
class StatusController extends Controller
{
    public function __invoke(AiClient $ai): JsonResponse
    {
        $online = Cache::remember('ai-service-online', now()->addSeconds(15), fn () => $ai->isHealthy());

        return response()->json(['ai' => $online]);
    }
}
