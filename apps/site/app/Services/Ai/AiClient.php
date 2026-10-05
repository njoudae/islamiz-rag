<?php

namespace App\Services\Ai;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;

/**
 * HTTP client for the Daleel AI service (FastAPI).
 *
 * This is the only class that knows the AI service's URLs and wire format.
 */
final readonly class AiClient
{
    public function __construct(
        private string $baseUrl,
        private ?string $token,
        private int $timeout,
        private int $connectTimeout,
    ) {}

    /**
     * @throws AiServiceException
     */
    public function ask(string $query, ?string $language = null, string $answerMode = 'text', ?string $conversationId = null): AiAnswer
    {
        try {
            $response = $this->request()
                ->timeout($this->timeout)
                ->post('/v1/ask', array_filter([
                    'query' => $query,
                    'language' => $language,
                    'answer_mode' => $answerMode,
                    'conversation_id' => $conversationId,
                ], fn ($value) => $value !== null));
        } catch (ConnectionException $exception) {
            throw AiServiceException::unreachable($exception);
        }

        if ($response->failed()) {
            throw AiServiceException::upstreamError($response->status(), Str::limit($response->body(), 500));
        }

        $payload = $response->json();

        if (! is_array($payload)) {
            throw AiServiceException::invalidResponse('body is not a JSON object');
        }

        return AiAnswer::fromResponse($payload);
    }

    /**
     * Model names and the real size of the knowledge base, or null when the AI service
     * is unreachable or predates the endpoint. Never throws: callers treat it as optional.
     *
     * @return ?array{models: array<string, string>, index: array<string, mixed>}
     */
    public function info(): ?array
    {
        try {
            $response = $this->request()->timeout(5)->get('/v1/info');
        } catch (ConnectionException) {
            return null;
        }

        $payload = $response->successful() ? $response->json() : null;

        return is_array($payload) && is_array($payload['index'] ?? null) && is_array($payload['models'] ?? null) ? $payload : null;
    }

    public function isHealthy(): bool
    {
        try {
            return $this->request()->timeout(3)->get('/health')->successful();
        } catch (ConnectionException) {
            return false;
        }
    }

    private function request(): PendingRequest
    {
        return Http::baseUrl($this->baseUrl)
            ->acceptJson()
            ->asJson()
            ->connectTimeout($this->connectTimeout)
            ->withHeaders(array_filter(['X-Internal-Token' => $this->token]));
    }
}
