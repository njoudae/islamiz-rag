<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Question;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Validation\Rule;

/**
 * Thumbs up or down on an answer, and the reason picked after a thumbs down.
 */
class FeedbackController extends Controller
{
    public function __invoke(Request $request, Question $question): Response
    {
        // Visitors have no accounts; only the browser that asked may rate the answer.
        $visitor = (string) $request->header('X-Visitor-Id');
        abort_unless($question->visitor_id !== null && hash_equals($question->visitor_id, $visitor), 403);

        $data = $request->validate([
            'value' => ['present', 'nullable', Rule::in(['up', 'down'])],
            'reason' => ['nullable', 'string', 'max:100'],
        ]);

        $question->forceFill([
            'feedback' => $data['value'],
            'feedback_reason' => $data['value'] === 'down' ? ($data['reason'] ?? null) : null,
            'feedback_at' => $data['value'] ? now() : null,
        ])->save();

        return response()->noContent();
    }
}
