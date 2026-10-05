<?php

namespace App\Services\Ai;

use App\Support\Arabic;
use Illuminate\Support\Facades\Cache;

/**
 * What the AI service actually has indexed and which models it runs, cached
 * briefly so pages never wait on it.
 */
final readonly class KnowledgeBase
{
    private const CACHE_KEY = 'ai-knowledge-base';

    public function __construct(private AiClient $ai) {}

    /**
     * @return ?array{models: array<string, string>, documents: int, chunks: int, indexedAt: ?string, books: list<array{title: string, entries: int}>, chapters: list<array{book: string, title: string, entries: int}>}
     */
    public function summary(): ?array
    {
        $cached = Cache::get(self::CACHE_KEY);

        if (is_array($cached)) {
            return $cached['value'];
        }

        $info = $this->ai->info();
        $value = $info ? $this->shape($info) : null;

        // Remember a miss only briefly, so the pages pick the data up soon after the AI service starts.
        Cache::put(self::CACHE_KEY, ['value' => $value], $value ? now()->addMinutes(10) : now()->addSeconds(30));

        return $value;
    }

    /**
     * @param  array{models: array<string, mixed>, index: array<string, mixed>}  $info
     */
    private function shape(array $info): array
    {
        $index = $info['index'];

        return [
            'models' => array_map('strval', array_filter($info['models'], 'is_string')),
            'documents' => (int) ($index['documents'] ?? 0),
            'chunks' => (int) ($index['chunks'] ?? 0),
            'indexedAt' => is_string($index['indexed_at'] ?? null) ? $index['indexed_at'] : null,
            'books' => array_values(array_map(fn (array $b) => [
                'title' => Arabic::stripDiacritics((string) ($b['title'] ?? '')),
                'entries' => (int) ($b['entries'] ?? 0),
            ], array_filter($index['books'] ?? [], 'is_array'))),
            'chapters' => array_values(array_map(fn (array $c) => [
                'book' => Arabic::stripDiacritics((string) ($c['book'] ?? '')),
                'title' => Arabic::stripDiacritics((string) ($c['title'] ?? '')),
                'entries' => (int) ($c['entries'] ?? 0),
            ], array_filter($index['chapters'] ?? [], 'is_array'))),
        ];
    }
}
