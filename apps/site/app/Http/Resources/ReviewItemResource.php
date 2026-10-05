<?php

namespace App\Http\Resources;

use App\Enums\AnswerState;
use App\Models\Question;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Str;

/**
 * A question as the review queue and its side sheet show it.
 *
 * @mixin Question
 */
class ReviewItemResource extends JsonResource
{
    /**
     * @return array<string, mixed>
     */
    public function toArray(Request $request): array
    {
        $citations = collect($this->citations ?? []);

        return [
            'id' => $this->id,
            'query' => $this->query,
            'context' => $this->parent?->query,
            'state' => $this->state->value,
            'channel' => $this->channel->value,
            'language' => $this->language,
            'reason' => $this->reviewReason(),
            'confidence' => $this->confidence,
            'book' => $this->book,
            'chapter' => $this->chapter,
            'state_reason' => $this->state_reason,
            'model_name' => $this->model,
            'source' => $citations->pluck('title')->filter()->first(),
            'sources' => $citations->map(fn (array $c) => ['title' => $c['title'] ?? null, 'url' => $c['source_url'] ?? null])->values(),
            'model' => $this->modelOutput(),
            'feedback' => $this->feedback,
            'feedback_reason' => $this->feedback_reason,
            'duration_ms' => $this->duration_ms,
            'error_code' => $this->error_code,
            'is_demo' => $this->is_demo,
            'created_at' => $this->created_at?->toIso8601String(),
            'review' => $this->review ? [
                'verdict' => $this->review->verdict->value,
                'label' => $this->review->label->value,
                'correction' => $this->review->correction,
                'citation_correct' => $this->review->citation_correct,
                'transcript_correction' => $this->review->transcript_correction,
                'add_to_eval' => $this->review->add_to_eval,
                'by' => $this->review->reviewer?->name,
            ] : null,
        ];
    }

    /**
     * What the visitor was shown, in one block of text.
     */
    private function modelOutput(): string
    {
        $text = match ($this->state) {
            AnswerState::Answerable => trim($this->summary."\n\n".$this->explanation),
            AnswerState::NeedsClarification => (string) $this->clarification_question,
            AnswerState::Failed => (string) $this->error_message,
            default => (string) $this->escalation_message,
        };

        return Str::limit($text, 2000);
    }
}
