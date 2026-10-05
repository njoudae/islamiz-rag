<?php

namespace App\Services\Analytics;

use App\Enums\AnswerState;
use App\Enums\Channel;
use App\Models\Question;
use App\Support\Arabic;
use Carbon\CarbonImmutable;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;

/**
 * Figures the admin pages derive from what the AI service reports about each
 * question (its section of the encyclopedia, model) and from the team's reviews.
 */
final class QuestionInsights
{
    /** Name of the bucket for questions no indexed passage is really about. */
    public const UNCOVERED = 'مسائل لا يغطيها الفهرس الحالي';

    /**
     * Questions per encyclopedia section, with how many were answered directly
     * and how many lacked evidence. Only questions tied to a section are counted.
     *
     * @return list<array{book: string, chapter: string, total: int, answered: int, insufficient: int}>
     */
    public function sections(CarbonImmutable $from, CarbonImmutable $to): array
    {
        $rows = Question::query()->toBase()
            ->selectRaw('book, chapter, state, count(*) as n')
            ->whereNotNull('chapter')
            ->where('created_at', '>=', $from->startOfDay())
            ->where('created_at', '<', $to->startOfDay()->addDay())
            ->groupBy('book', 'chapter', 'state')
            ->get();

        $sections = [];
        foreach ($rows as $row) {
            $key = $row->book.'|'.$row->chapter;
            $sections[$key] ??= ['book' => (string) $row->book, 'chapter' => (string) $row->chapter, 'total' => 0, 'answered' => 0, 'insufficient' => 0];
            $sections[$key]['total'] += (int) $row->n;
            $sections[$key]['answered'] += $row->state === AnswerState::Answerable->value ? (int) $row->n : 0;
            $sections[$key]['insufficient'] += $row->state === AnswerState::InsufficientEvidence->value ? (int) $row->n : 0;
        }

        usort($sections, fn ($a, $b) => $b['total'] <=> $a['total']);

        return array_values($sections);
    }

    /**
     * Unanswered questions grouped into gaps, with the change against the previous window.
     *
     * Questions without enough evidence are grouped by the section their nearest passage
     * belongs to, or into one "not covered" bucket when nothing indexed is close.
     * Out-of-scope questions are grouped when the same question is asked repeatedly.
     *
     * @return array{insufficient: list<array<string, mixed>>, outOfScope: list<array<string, mixed>>}
     */
    public function gaps(CarbonImmutable $from, CarbonImmutable $to, CarbonImmutable $previousFrom): array
    {
        $rows = Question::query()
            ->whereIn('state', [AnswerState::InsufficientEvidence, AnswerState::OutOfScope])
            ->where('created_at', '>=', $previousFrom->startOfDay())
            ->where('created_at', '<', $to->startOfDay()->addDay())
            ->latest()
            ->limit(5000)
            ->get(['id', 'query', 'state', 'book', 'chapter', 'created_at']);

        $isCurrent = fn (Question $q) => $q->created_at >= $from->startOfDay();

        $insufficient = $this->groupGaps(
            $rows->where('state', AnswerState::InsufficientEvidence),
            'insufficient',
            fn (Question $q) => $q->chapter ?? self::UNCOVERED,
            fn (Question $q) => $q->chapter ?? self::UNCOVERED,
            $isCurrent,
        );

        $outOfScope = $this->groupGaps(
            $rows->where('state', AnswerState::OutOfScope),
            'out_of_scope',
            fn (Question $q) => Arabic::normalize($q->query),
            fn (Question $q) => $q->query,
            $isCurrent,
        );

        return ['insufficient' => $insufficient, 'outOfScope' => $outOfScope];
    }

    /**
     * @param  Collection<int, Question>  $rows  Newest first.
     * @return list<array<string, mixed>>
     */
    private function groupGaps(Collection $rows, string $kind, callable $keyOf, callable $titleOf, callable $isCurrent): array
    {
        $groups = [];

        foreach ($rows as $question) {
            $key = $keyOf($question);
            $groups[$key] ??= [
                'key' => substr(sha1($kind.'|'.$key), 0, 40),
                'kind' => $kind,
                'title' => $titleOf($question),
                'book' => $question->chapter ? $question->book : null,
                'n' => 0,
                'previous' => 0,
                'examples' => [],
            ];

            if ($isCurrent($question)) {
                $groups[$key]['n']++;
                if (count($groups[$key]['examples']) < 2 && ! in_array($question->query, $groups[$key]['examples'], true)) {
                    $groups[$key]['examples'][] = $question->query;
                }
            } else {
                $groups[$key]['previous']++;
            }
        }

        $groups = array_filter($groups, fn (array $g) => $g['n'] > 0);
        usort($groups, fn ($a, $b) => $b['n'] <=> $a['n']);

        return array_map(fn (array $g) => [
            ...$g,
            'delta' => $g['previous'] > 0 ? (int) round(($g['n'] - $g['previous']) / $g['previous'] * 100) : null,
        ], array_slice(array_values($groups), 0, 8));
    }

    /**
     * One row per generation model seen in the question log, oldest first, with the
     * quality figures the reviews support. This is the real "version comparison".
     *
     * @return list<array<string, mixed>>
     */
    public function versions(): array
    {
        $models = Question::query()->toBase()
            ->whereNotNull('model')
            ->selectRaw('model, count(*) as n, min(created_at) as first_seen')
            ->groupBy('model')
            ->orderBy('first_seen')
            ->get();

        $reviews = DB::table('question_reviews')
            ->join('questions', 'questions.id', '=', 'question_reviews.question_id')
            ->whereNotNull('questions.model')
            ->get(['questions.model', 'questions.state', 'question_reviews.label', 'question_reviews.citation_correct'])
            ->groupBy('model');

        return $models->map(function ($row) use ($reviews) {
            $reviewed = ($reviews[$row->model] ?? collect())->filter(
                fn ($r) => $r->state !== AnswerState::Failed->value && $r->label !== AnswerState::Failed->value,
            );
            $share = fn (Collection $set, callable $hit) => $set->isEmpty() ? null : round($set->filter($hit)->count() / $set->count() * 100, 1);
            $cited = $reviewed->filter(fn ($r) => $r->citation_correct !== null);

            $durations = Question::query()
                ->where('model', $row->model)
                ->where('state', '!=', AnswerState::Failed)
                ->whereNotNull('duration_ms')
                ->orderBy('duration_ms')
                ->pluck('duration_ms')
                ->all();

            return [
                'model' => $row->model,
                'questions' => (int) $row->n,
                'firstSeen' => CarbonImmutable::parse($row->first_seen)->toIso8601String(),
                'reviewed' => $reviewed->count(),
                'accuracy' => $share($reviewed, fn ($r) => $r->label === $r->state),
                'citation' => $share($cited, fn ($r) => (bool) $r->citation_correct),
                'clarification' => $share(
                    $reviewed->where('label', AnswerState::NeedsClarification->value),
                    fn ($r) => $r->state === AnswerState::NeedsClarification->value,
                ),
                'referral' => $share(
                    $reviewed->where('label', AnswerState::ComplexCase->value),
                    fn ($r) => $r->state === AnswerState::ComplexCase->value,
                ),
                'p95' => $durations === [] ? null : round($durations[max(0, (int) ceil(0.95 * count($durations)) - 1)] / 1000, 1),
            ];
        })->all();
    }

    /**
     * Share of reviewed answers whose cited sources the reviewer confirmed.
     *
     * @return array{value: ?float, judged: int}
     */
    public function citationAccuracy(): array
    {
        $judged = DB::table('question_reviews')->whereNotNull('citation_correct')->count();
        $correct = DB::table('question_reviews')->where('citation_correct', true)->count();

        return ['value' => $judged ? round($correct / $judged, 4) : null, 'judged' => $judged];
    }

    /**
     * Voice transcription quality over every reviewed voice question. A reviewer who leaves
     * the transcript alone confirms it; one who rewrites it supplies what was really said.
     * Gives the word error rate and the word pairs most often confused.
     *
     * @return array{wer: ?float, samples: int, terms: list<array{right: string, wrong: string, n: int}>}
     */
    public function transcription(): array
    {
        $pairs = DB::table('question_reviews')
            ->join('questions', 'questions.id', '=', 'question_reviews.question_id')
            ->where('questions.channel', Channel::Voice->value)
            ->get(['questions.query as heard', 'question_reviews.transcript_correction as said']);

        $errors = 0;
        $words = 0;
        $confusions = [];

        foreach ($pairs as $pair) {
            $reference = Arabic::words((string) ($pair->said ?: $pair->heard));
            $hypothesis = Arabic::words((string) $pair->heard);
            if ($reference === []) {
                continue;
            }

            [$distance, $substitutions] = $this->align($reference, $hypothesis);
            $errors += $distance;
            $words += count($reference);

            foreach ($substitutions as [$right, $wrong]) {
                $confusions[$right.'|'.$wrong] = ($confusions[$right.'|'.$wrong] ?? 0) + 1;
            }
        }

        arsort($confusions);

        return [
            'wer' => $words ? round($errors / $words, 4) : null,
            'samples' => $pairs->count(),
            'terms' => array_map(function (string $key, int $n) {
                [$right, $wrong] = explode('|', $key);

                return ['right' => $right, 'wrong' => $wrong, 'n' => $n];
            }, array_keys(array_slice($confusions, 0, 5, true)), array_slice($confusions, 0, 5, true)),
        ];
    }

    /**
     * Word-level edit distance between what was said and what was heard, with the
     * substituted word pairs along the cheapest alignment.
     *
     * @param  list<string>  $reference
     * @param  list<string>  $hypothesis
     * @return array{0: int, 1: list<array{0: string, 1: string}>}
     */
    private function align(array $reference, array $hypothesis): array
    {
        $n = count($reference);
        $m = count($hypothesis);
        $d = [];
        for ($i = 0; $i <= $n; $i++) {
            $d[$i][0] = $i;
        }
        for ($j = 0; $j <= $m; $j++) {
            $d[0][$j] = $j;
        }
        for ($i = 1; $i <= $n; $i++) {
            for ($j = 1; $j <= $m; $j++) {
                $cost = $reference[$i - 1] === $hypothesis[$j - 1] ? 0 : 1;
                $d[$i][$j] = min($d[$i - 1][$j] + 1, $d[$i][$j - 1] + 1, $d[$i - 1][$j - 1] + $cost);
            }
        }

        $substitutions = [];
        for ($i = $n, $j = $m; $i > 0 && $j > 0;) {
            if ($reference[$i - 1] === $hypothesis[$j - 1]) {
                $i--;
                $j--;
            } elseif ($d[$i][$j] === $d[$i - 1][$j - 1] + 1) {
                $substitutions[] = [$reference[$i - 1], $hypothesis[$j - 1]];
                $i--;
                $j--;
            } elseif ($d[$i][$j] === $d[$i - 1][$j] + 1) {
                $i--;
            } else {
                $j--;
            }
        }

        return [$d[$n][$m], $substitutions];
    }
}
