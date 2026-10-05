<?php

namespace App\Http\Resources;

use App\Models\Question;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Public answer payload. Field names match the AI service's AnswerResponse,
 * so the frontend contract did not change when this backend was introduced.
 *
 * @mixin Question
 */
class AnswerResource extends JsonResource
{
    public static $wrap = null;

    /**
     * @return array<string, mixed>
     */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'state' => $this->state->value,
            'language' => $this->language,
            'summary' => $this->summary,
            'explanation' => $this->explanation,
            'clarification_question' => $this->clarification_question,
            'escalation_message' => $this->escalation_message,
            'citations' => $this->citations ?? [],
        ];
    }
}
