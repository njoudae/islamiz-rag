<?php

namespace App\Actions;

use App\Enums\AnswerState;
use App\Enums\Channel;
use App\Models\Question;
use App\Services\Ai\AiClient;
use App\Services\Ai\AiServiceException;
use Illuminate\Support\Str;

/**
 * Sends a visitor's question to the AI service and records the outcome.
 *
 * Every question is stored, including the ones the AI service could not
 * process, so the admin area reflects what visitors actually experienced.
 */
final readonly class AskQuestion
{
    public function __construct(private AiClient $ai) {}

    /**
     * @param  ?Question  $parent  The question this one continues, such as the one that asked for clarification.
     * @param  array{visitor_id?: ?string, ip?: ?string, user_agent?: ?string}  $visitor
     */
    public function handle(
        string $query,
        ?string $language = null,
        string $answerMode = 'text',
        Channel $channel = Channel::Text,
        ?Question $parent = null,
        array $visitor = [],
    ): Question {
        $visitorId = $visitor['visitor_id'] ?? null;

        // Only continue a conversation the same visitor started.
        if ($parent && $parent->visitor_id !== $visitorId) {
            $parent = null;
        }

        // The AI service is stateless, so a follow-up is sent together with the question it answers.
        $aiQuery = $parent ? $parent->query."\n".$query : $query;

        $startedAt = hrtime(true);

        try {
            $answer = $this->ai->ask($aiQuery, $language, $answerMode);

            $outcome = [
                'state' => $answer->state,
                'language' => $answer->language ?? $language,
                'summary' => $answer->summary,
                'explanation' => $answer->explanation,
                'clarification_question' => $answer->clarificationQuestion,
                'escalation_message' => $answer->escalationMessage,
                'citations' => $answer->citations,
                'book' => $answer->book(),
                'chapter' => $answer->chapter(),
                'related' => $answer->related,
                'confidence' => $answer->confidence(),
                'state_reason' => Str::limit(implode('; ', $answer->reasons), 290, '') ?: null,
                'model' => $answer->model,
            ];
        } catch (AiServiceException $exception) {
            report($exception);

            $outcome = [
                'state' => AnswerState::Failed,
                'language' => $language,
                'citations' => [],
                'error_code' => $exception->reason,
                'error_message' => Str::limit($exception->getMessage(), 1000),
            ];
        }

        return Question::create([
            'parent_id' => $parent?->id,
            'query' => $query,
            'answer_mode' => $answerMode,
            'channel' => $channel,
            'duration_ms' => intdiv(hrtime(true) - $startedAt, 1_000_000),
            'visitor_id' => $visitorId,
            'ip_hash' => isset($visitor['ip']) ? hash_hmac('sha256', $visitor['ip'], (string) config('app.key')) : null,
            'user_agent' => isset($visitor['user_agent']) ? Str::limit($visitor['user_agent'], 500, '') : null,
            ...$outcome,
        ]);
    }
}
