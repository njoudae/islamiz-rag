<?php

namespace App\Services\Analytics;

use App\Enums\AnswerState;
use App\Enums\Channel;
use App\Models\Question;
use Carbon\CarbonImmutable;

/**
 * Aggregates the question log for the admin dashboards.
 *
 * Grouping happens in SQL by day, state, channel and feedback, so the cost
 * grows with the number of days shown, not with the number of questions.
 */
final class QuestionAnalytics
{
    /**
     * One row per calendar day from $from to $to inclusive, with zero rows for quiet days.
     *
     * @return list<array{date: string, total: int, voice: int, voiceFailed: int, textFailed: int, rated: int, up: int, c: array<string, int>}>
     */
    public function daily(CarbonImmutable $from, CarbonImmutable $to): array
    {
        $days = [];
        for ($day = $from->startOfDay(); $day <= $to; $day = $day->addDay()) {
            $days[$day->toDateString()] = [
                'date' => $day->toDateString(),
                'total' => 0, 'voice' => 0, 'voiceFailed' => 0, 'textFailed' => 0, 'rated' => 0, 'up' => 0,
                'c' => array_fill_keys(array_map(fn (AnswerState $s) => $s->value, AnswerState::cases()), 0),
            ];
        }

        $rows = Question::query()->toBase()
            ->selectRaw('date(created_at) as day, state, channel, feedback, count(*) as n')
            ->where('created_at', '>=', $from->startOfDay())
            ->where('created_at', '<', $to->startOfDay()->addDay())
            ->groupBy('day', 'state', 'channel', 'feedback')
            ->get();

        foreach ($rows as $row) {
            $key = substr((string) $row->day, 0, 10);
            if (! isset($days[$key])) {
                continue;
            }

            $n = (int) $row->n;
            $failed = $row->state === AnswerState::Failed->value;
            $voice = $row->channel === Channel::Voice->value;

            $days[$key]['total'] += $n;
            $days[$key]['c'][$row->state] = ($days[$key]['c'][$row->state] ?? 0) + $n;
            $days[$key]['voice'] += $voice ? $n : 0;
            $days[$key]['voiceFailed'] += $voice && $failed ? $n : 0;
            $days[$key]['textFailed'] += ! $voice && $failed ? $n : 0;
            $days[$key]['rated'] += $row->feedback !== null ? $n : 0;
            $days[$key]['up'] += $row->feedback === 'up' ? $n : 0;
        }

        return array_values($days);
    }

    /**
     * Median and 95th-percentile answer time in seconds, for questions that got a response.
     *
     * @return array{p50: ?float, p95: ?float}
     */
    public function latency(CarbonImmutable $from, CarbonImmutable $to): array
    {
        $durations = Question::query()
            ->where('created_at', '>=', $from->startOfDay())
            ->where('created_at', '<', $to->startOfDay()->addDay())
            ->where('state', '!=', AnswerState::Failed)
            ->whereNotNull('duration_ms')
            ->orderBy('duration_ms')
            ->pluck('duration_ms')
            ->all();

        return [
            'p50' => $this->percentile($durations, 0.50),
            'p95' => $this->percentile($durations, 0.95),
        ];
    }

    /**
     * @param  list<int>  $sorted  Durations in milliseconds, ascending.
     */
    private function percentile(array $sorted, float $p): ?float
    {
        if ($sorted === []) {
            return null;
        }

        $index = max(0, (int) ceil($p * count($sorted)) - 1);

        return round($sorted[$index] / 1000, 2);
    }
}
