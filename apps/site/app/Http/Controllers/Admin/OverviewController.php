<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Http\Requests\Admin\PeriodRequest;
use App\Models\ContactMessage;
use App\Models\Question;
use App\Services\Analytics\QuestionAnalytics;
use App\Services\Analytics\QuestionInsights;
use Carbon\CarbonImmutable;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;

class OverviewController extends Controller
{
    public function __invoke(PeriodRequest $request, QuestionAnalytics $analytics, QuestionInsights $insights): Response
    {
        $period = $request->period();
        $start = $request->windowStart();
        $today = CarbonImmutable::today();
        $previousStart = $start->subDays($period);
        $previousEnd = $start->subDay();

        $days = $analytics->daily($previousStart, $today);

        return Inertia::render('admin/Overview', [
            'period' => $period,
            // The previous window followed by the current one; the page splits them.
            'days' => $days,
            'sections' => array_slice($insights->sections($start, $today), 0, 7),
            'transcription' => $insights->transcription(),
            'events' => $this->events(array_slice($days, $period), $insights->versions()),
            'latency' => [
                'current' => $analytics->latency($start, $today),
                'previous' => $analytics->latency($previousStart, $previousEnd),
            ],
            'recent' => Question::latest()->limit(6)->get()->map(fn (Question $q) => [
                'id' => $q->id,
                'query' => $q->query,
                'state' => $q->state->value,
                'channel' => $q->channel->value,
                'feedback' => $q->feedback,
                'feedback_reason' => $q->feedback_reason,
                'is_demo' => $q->is_demo,
                'created_at' => $q->created_at?->toIso8601String(),
            ]),
            // The newest messages from the contact page, so they are seen without opening the inbox.
            'messages' => ContactMessage::latest()->limit(5)->get()->map(fn (ContactMessage $m) => [
                'id' => $m->id,
                'name' => $m->name,
                'topic_label' => $m->topic->label(),
                'message' => Str::limit($m->message, 160),
                'status' => $m->status->value,
                'created_at' => $m->created_at?->toIso8601String(),
            ]),
        ]);
    }

    /**
     * Things worth marking on the trend chart, all derived from the log itself: the day
     * a new generation model first answered, and days when most questions failed.
     *
     * @param  list<array<string, mixed>>  $days  The current window.
     * @param  list<array<string, mixed>>  $versions  Oldest first.
     * @return list<array{date: string, label: string}>
     */
    private function events(array $days, array $versions): array
    {
        $events = [];

        // The first model is the starting point, not a change.
        foreach (array_slice($versions, 1) as $version) {
            $events[] = ['date' => substr($version['firstSeen'], 0, 10), 'label' => $version['model']];
        }

        foreach ($days as $day) {
            $failed = $day['c']['FAILED'] ?? 0;
            if ($day['total'] >= 3 && $failed / $day['total'] >= 0.5) {
                $events[] = ['date' => $day['date'], 'label' => 'تعطّل الخدمة'];
            }
        }

        return $events;
    }
}
