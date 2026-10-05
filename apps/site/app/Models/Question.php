<?php

namespace App\Models;

use App\Enums\AnswerState;
use App\Enums\Channel;
use Database\Factories\QuestionFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Scope;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;

/**
 * One question asked by a visitor, together with what the AI service returned.
 */
#[Fillable([
    'parent_id', 'conversation_id', 'query', 'language', 'answer_mode', 'channel', 'state', 'summary', 'explanation',
    'clarification_question', 'escalation_message', 'citations',
    'book', 'chapter', 'related', 'confidence', 'state_reason', 'model',
    'error_code', 'error_message', 'duration_ms', 'visitor_id', 'ip_hash', 'user_agent',
])]
class Question extends Model
{
    /** @use HasFactory<QuestionFactory> */
    use HasFactory;

    /**
     * Defaults that the database also applies, so a freshly created model is complete without a reload.
     *
     * @var array<string, mixed>
     */
    protected $attributes = [
        'channel' => 'text',
        'is_demo' => false,
    ];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'state' => AnswerState::class,
            'channel' => Channel::class,
            'citations' => 'array',
            'related' => 'array',
            'confidence' => 'integer',
            'duration_ms' => 'integer',
            'feedback_at' => 'datetime',
            'is_demo' => 'boolean',
        ];
    }

    /**
     * @return BelongsTo<Question, $this>
     */
    public function parent(): BelongsTo
    {
        return $this->belongsTo(Question::class, 'parent_id');
    }

    /**
     * @return HasOne<QuestionReview, $this>
     */
    public function review(): HasOne
    {
        return $this->hasOne(QuestionReview::class);
    }

    /**
     * Questions the visitor left without an answer or a follow-up question.
     *
     * @param  Builder<self>  $query
     */
    #[Scope]
    protected function unanswered(Builder $query): void
    {
        $query->whereIn('state', AnswerState::unanswered());
    }

    /**
     * @param  Builder<self>  $query
     */
    #[Scope]
    protected function awaitingReview(Builder $query): void
    {
        $query->whereDoesntHave('review');
    }

    /**
     * Why this question deserves a human look, in the order the review queue cares about.
     */
    public function reviewReason(): string
    {
        return match (true) {
            $this->feedback === 'down' => 'تقييم سلبي',
            $this->state === AnswerState::Failed => 'فشل تقني',
            $this->state === AnswerState::ComplexCase => 'تحقّق من الإحالة',
            in_array($this->state, [AnswerState::InsufficientEvidence, AnswerState::OutOfScope], true) => 'فجوة معرفية',
            $this->state === AnswerState::ConflictingEvidence => 'تحقّق من نسبة الأقوال',
            default => 'عيّنة للمراجعة',
        };
    }
}
