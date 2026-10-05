<?php

namespace App\Models;

use App\Enums\AnswerState;
use App\Enums\ReviewVerdict;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * A team member's verdict on one answer.
 */
#[Fillable(['verdict', 'label', 'citation_correct', 'correction', 'transcript_correction', 'add_to_eval'])]
class QuestionReview extends Model
{
    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'verdict' => ReviewVerdict::class,
            'label' => AnswerState::class,
            'add_to_eval' => 'boolean',
            'citation_correct' => 'boolean',
        ];
    }

    /**
     * @return BelongsTo<Question, $this>
     */
    public function question(): BelongsTo
    {
        return $this->belongsTo(Question::class);
    }

    /**
     * @return BelongsTo<User, $this>
     */
    public function reviewer(): BelongsTo
    {
        return $this->belongsTo(User::class, 'reviewer_id');
    }
}
