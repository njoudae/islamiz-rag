<?php

namespace Database\Factories;

use App\Enums\AnswerState;
use App\Enums\Channel;
use App\Models\Question;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Question>
 */
class QuestionFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'query' => 'أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟',
            'language' => 'ar',
            'answer_mode' => 'text',
            'channel' => Channel::Text,
            'state' => AnswerState::Answerable,
            'summary' => 'ملخص تجريبي مبني على المصدر.',
            'citations' => [[
                'fatwa_id' => 1455,
                'title' => 'المطلب الثاني: عدم نية الإقامة في السفر',
                'source_url' => 'https://dorar.net/feqhia/1455/x',
            ]],
            'duration_ms' => fake()->numberBetween(800, 9000),
            'visitor_id' => fake()->uuid(),
        ];
    }

    public function voice(): static
    {
        return $this->state(fn () => ['channel' => Channel::Voice]);
    }

    /**
     * A question that ended in the given non-answer state.
     */
    public function withOutcome(AnswerState $state): static
    {
        return $this->state(fn () => [
            'state' => $state,
            'summary' => null,
            'citations' => [],
            'clarification_question' => $state === AnswerState::NeedsClarification ? 'كم تنوي الإقامة في وجهتك؟' : null,
            'escalation_message' => in_array($state, [AnswerState::NeedsClarification, AnswerState::Failed], true) ? null : 'هذه المسألة تحتاج نظرًا من مختص.',
            'error_code' => $state === AnswerState::Failed ? 'unreachable' : null,
            'error_message' => $state === AnswerState::Failed ? 'Connection refused' : null,
            'duration_ms' => $state === AnswerState::Failed ? null : fake()->numberBetween(800, 9000),
        ]);
    }
}
