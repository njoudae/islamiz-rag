<?php

namespace App\Http\Controllers\Admin;

use App\Enums\AnswerState;
use App\Enums\Channel;
use App\Enums\ReviewVerdict;
use App\Http\Controllers\Controller;
use App\Http\Resources\ReviewItemResource;
use App\Models\Question;
use App\Models\QuestionReview;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

/**
 * The review queue: every question, newest first, with the team's verdicts.
 */
class ReviewController extends Controller
{
    public function index(Request $request): Response
    {
        $filters = $request->validate([
            'filter' => ['nullable', Rule::in(['pending', 'done', 'all'])],
            'state' => ['nullable', Rule::in(['ALL', ...array_map(fn (AnswerState $s) => $s->value, AnswerState::cases())])],
            'channel' => ['nullable', Rule::in(['all', ...array_map(fn (Channel $c) => $c->value, Channel::cases())])],
            'search' => ['nullable', 'string', 'max:200'],
        ]) + ['filter' => 'pending', 'state' => 'ALL', 'channel' => 'all', 'search' => null];

        $filters['filter'] ??= 'pending';
        $filters['state'] ??= 'ALL';
        $filters['channel'] ??= 'all';

        // Everything except the pending/done split, so the tab counts follow the other filters.
        $base = fn (): Builder => Question::query()
            ->when($filters['state'] !== 'ALL', fn (Builder $q) => $q->where('state', $filters['state']))
            ->when($filters['channel'] !== 'all', fn (Builder $q) => $q->where('channel', $filters['channel']))
            ->when($filters['search'], fn (Builder $q, string $s) => $q->whereLike('query', "%{$s}%"));

        $questions = $base()
            ->when($filters['filter'] === 'pending', fn (Builder $q) => $q->awaitingReview())
            ->when($filters['filter'] === 'done', fn (Builder $q) => $q->has('review'))
            ->with(['review.reviewer', 'parent'])
            ->latest()
            ->paginate(25)
            ->withQueryString();

        return Inertia::render('admin/Review', [
            'questions' => ReviewItemResource::collection($questions),
            'filters' => $filters,
            'tabCounts' => [
                'pending' => $base()->awaitingReview()->count(),
                'done' => $base()->has('review')->count(),
                'all' => $base()->count(),
            ],
            'kpis' => [
                'pending' => Question::awaitingReview()->count(),
                'negative' => Question::awaitingReview()->where('feedback', 'down')->count(),
                // Answers given although the best passage matched weakly.
                'lowConfidence' => Question::awaitingReview()->where('state', AnswerState::Answerable)->where('confidence', '<', 70)->count(),
                'reviewedToday' => QuestionReview::where('reviewer_id', $request->user()->id)->whereDate('updated_at', today())->count(),
            ],
        ]);
    }

    public function store(Request $request, Question $question): RedirectResponse
    {
        $data = $request->validate([
            'verdict' => ['required', Rule::enum(ReviewVerdict::class)],
            'label' => ['required', Rule::enum(AnswerState::class)],
            'citation_correct' => ['nullable', 'boolean'],
            'correction' => ['nullable', 'string', 'max:5000'],
            'transcript_correction' => ['nullable', 'string', 'max:4000'],
            'add_to_eval' => ['boolean'],
        ], [
            'verdict.required' => 'اختر حكماً على الإجابة قبل الحفظ.',
        ]);

        $review = $question->review()->firstOrNew();
        $review->fill([...$data, 'add_to_eval' => $request->boolean('add_to_eval', true)]);
        $review->reviewer()->associate($request->user());
        $review->save();

        $label = AnswerState::from($data['label']);

        return back()->with('toast', $label !== $question->state
            ? "حُفظت المراجعة، وسُجّل التصحيح إلى «{$label->label()}»."
            : 'حُفظت المراجعة.');
    }
}
