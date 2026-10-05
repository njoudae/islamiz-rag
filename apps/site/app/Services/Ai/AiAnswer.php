<?php

namespace App\Services\Ai;

use App\Enums\AnswerState;
use App\Support\Arabic;

/**
 * The AI service's answer to one question, validated at the boundary.
 */
final readonly class AiAnswer
{
    /**
     * Below this reranker score the "nearest" passage is not about the question at all,
     * so its book and chapter say nothing. Matches the evidence gate's own floor.
     */
    private const RELEVANT_SCORE = 0.05;

    /**
     * @param  list<array<string, mixed>>  $citations
     * @param  list<array<string, mixed>>  $related  Passages the pipeline considered, best first.
     * @param  ?float  $evidenceScore  Best reranker score, 0 to 1.
     * @param  list<string>  $reasons  Why the evidence gate chose this state.
     */
    public function __construct(
        public AnswerState $state,
        public ?string $language,
        public ?string $summary,
        public ?string $explanation,
        public ?string $clarificationQuestion,
        public ?string $escalationMessage,
        public array $citations,
        public array $related = [],
        public ?float $evidenceScore = null,
        public array $reasons = [],
        public ?string $model = null,
    ) {}

    /**
     * @param  array<string, mixed>  $payload
     *
     * @throws AiServiceException
     */
    public static function fromResponse(array $payload): self
    {
        $state = is_string($payload['state'] ?? null) ? AnswerState::tryFrom($payload['state']) : null;

        // FAILED is ours to assign; the AI service must never report it.
        if ($state === null || $state === AnswerState::Failed) {
            throw AiServiceException::invalidResponse('missing or unknown "state"');
        }

        $citations = $payload['citations'] ?? [];

        if (! is_array($citations)) {
            throw AiServiceException::invalidResponse('"citations" is not a list');
        }

        $score = $payload['evidence_score'] ?? null;

        return new self(
            state: $state,
            language: self::stringOrNull($payload['language'] ?? null),
            summary: self::stringOrNull($payload['summary'] ?? null),
            explanation: self::stringOrNull($payload['explanation'] ?? null),
            clarificationQuestion: self::stringOrNull($payload['clarification_question'] ?? null),
            escalationMessage: self::stringOrNull($payload['escalation_message'] ?? null),
            citations: array_values(array_filter($citations, 'is_array')),
            // Optional diagnostics: an older AI service simply does not send them.
            related: array_values(array_filter(is_array($payload['related'] ?? null) ? $payload['related'] : [], 'is_array')),
            evidenceScore: is_numeric($score) ? max(0.0, min(1.0, (float) $score)) : null,
            reasons: array_values(array_filter(is_array($payload['reasons'] ?? null) ? $payload['reasons'] : [], 'is_string')),
            model: self::stringOrNull($payload['model'] ?? null),
        );
    }

    /**
     * Best reranker score as a 0 to 100 integer, or null when the service did not report one.
     */
    public function confidence(): ?int
    {
        return $this->evidenceScore === null ? null : (int) round($this->evidenceScore * 100);
    }

    /**
     * The encyclopedia path of the passage this question is really about: the first cited
     * passage, or else the best related one when it matches well enough to mean something.
     *
     * @return list<string>
     */
    public function sourcePath(): array
    {
        $cited = $this->citations[0]['category_path'] ?? null;

        if (is_array($cited) && $cited !== []) {
            return self::cleanPath($cited);
        }

        $nearest = $this->related[0] ?? null;

        if ($nearest && (float) ($nearest['reranker_score'] ?? 0) >= self::RELEVANT_SCORE && is_array($nearest['category_path'] ?? null)) {
            return self::cleanPath($nearest['category_path']);
        }

        return [];
    }

    public function book(): ?string
    {
        return $this->sourcePath()[0] ?? null;
    }

    /**
     * The section used for grouping: the third level (الفصل) when the path has one.
     */
    public function chapter(): ?string
    {
        $path = $this->sourcePath();

        return $path[2] ?? $path[1] ?? null;
    }

    /**
     * @param  array<mixed>  $path
     * @return list<string>
     */
    private static function cleanPath(array $path): array
    {
        return array_values(array_map(
            fn ($part) => Arabic::stripDiacritics((string) $part),
            array_filter($path, fn ($part) => is_string($part) && $part !== ''),
        ));
    }

    private static function stringOrNull(mixed $value): ?string
    {
        return is_string($value) && $value !== '' ? $value : null;
    }
}
