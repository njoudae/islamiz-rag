<?php

namespace App\Http\Controllers\Admin;

use App\Enums\AnswerState;
use App\Http\Controllers\Controller;
use App\Models\Question;
use App\Models\QuestionReview;
use App\Services\Ai\AiServiceException;
use App\Services\Analytics\QuestionInsights;
use Illuminate\Support\Facades\DB;
use Inertia\Inertia;
use Inertia\Response;
use Symfony\Component\HttpFoundation\StreamedResponse;

/**
 * Model quality, measured against the team's reviews.
 */
class QualityController extends Controller
{
    /** Labels for the failure codes recorded by App\Actions\AskQuestion. */
    private const FAILURE_LABELS = [
        AiServiceException::UNREACHABLE => 'تعذّر الوصول إلى خدمة الذكاء الاصطناعي',
        AiServiceException::UPSTREAM_ERROR => 'خطأ داخل خدمة الذكاء الاصطناعي',
        AiServiceException::INVALID_RESPONSE => 'استجابة غير صالحة من الخدمة',
    ];

    public function index(QuestionInsights $insights): Response
    {
        $since = now()->subDays(30);

        // Reviewer label (rows) against the state the system returned (columns). FAILED is a
        // technical error rather than a classification, so it stays out of the matrix.
        $pairs = DB::table('question_reviews')
            ->join('questions', 'questions.id', '=', 'question_reviews.question_id')
            ->where('questions.state', '!=', AnswerState::Failed->value)
            ->where('question_reviews.label', '!=', AnswerState::Failed->value)
            ->groupBy('question_reviews.label', 'questions.state')
            ->selectRaw('question_reviews.label as gold, questions.state as predicted, count(*) as n')
            ->get();

        $failures = Question::query()->toBase()
            ->where('state', AnswerState::Failed->value)
            ->where('created_at', '>=', $since)
            ->groupBy('error_code')
            ->selectRaw('error_code, count(*) as n')
            ->orderByDesc('n')
            ->get()
            ->map(fn ($row) => ['label' => self::FAILURE_LABELS[$row->error_code] ?? 'سبب غير معروف', 'n' => (int) $row->n]);

        $feedbackReasons = Question::query()->toBase()
            ->where('feedback', 'down')
            ->where('feedback_at', '>=', $since)
            ->groupBy('feedback_reason')
            ->selectRaw('feedback_reason, count(*) as n')
            ->orderByDesc('n')
            ->get()
            ->map(fn ($row) => ['label' => $row->feedback_reason ?: 'بلا سبب محدد', 'n' => (int) $row->n]);

        return Inertia::render('admin/Quality', [
            'pairs' => $pairs->map(fn ($p) => ['gold' => $p->gold, 'predicted' => $p->predicted, 'n' => (int) $p->n]),
            'failures' => $failures,
            'failedTotal' => $failures->sum('n'),
            'feedbackReasons' => $feedbackReasons,
            'reviewed' => QuestionReview::count(),
            'evalSize' => QuestionReview::where('add_to_eval', true)->count(),
            'citationAccuracy' => $insights->citationAccuracy(),
            'versions' => $insights->versions(),
            'transcription' => $insights->transcription(),
        ]);
    }

    /**
     * Reviewed questions with their correct state, as a JSON evaluation set for the AI team.
     */
    public function export(): StreamedResponse
    {
        $rows = QuestionReview::query()
            ->with('question')
            ->where('add_to_eval', true)
            ->orderBy('id')
            ->get()
            ->map(fn (QuestionReview $r) => [
                'question' => $r->question->query,
                'channel' => $r->question->channel->value,
                'predicted_status' => $r->question->state->value,
                'gold_status' => $r->label->value,
                'verdict' => $r->verdict->value,
                'correction' => $r->correction ?? '',
                'citation_correct' => $r->citation_correct,
                'transcript_correction' => $r->transcript_correction,
                'model' => $r->question->model,
                'sources' => collect($r->question->citations ?? [])->pluck('title')->filter()->values(),
            ]);

        return response()->streamDownload(
            fn () => print (json_encode($rows, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)),
            'daleel-eval-set.json',
            ['Content-Type' => 'application/json; charset=utf-8'],
        );
    }
}
