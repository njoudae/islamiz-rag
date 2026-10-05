<?php

namespace App\Console\Commands;

use App\Enums\AnswerState;
use App\Enums\Channel;
use App\Models\Question;
use Carbon\CarbonImmutable;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Fills the question log with synthetic history so the dashboards can be
 * shown before real traffic exists. Every row is flagged `is_demo`, the admin
 * area labels it, and `--purge` removes it.
 */
class DemoData extends Command
{
    protected $signature = 'daleel:demo-data
        {--days=90 : How many days of history to generate}
        {--per-day=40 : Average questions per day}
        {--purge : Delete all demo rows instead of creating them}
        {--if-missing : Do nothing when demo rows already exist (used on container start)}';

    protected $description = 'Create or remove clearly labelled demo questions for the admin dashboards';

    /** Share of each state among demo questions. */
    private const SHARES = [
        'ANSWERABLE' => .58, 'NEEDS_CLARIFICATION' => .10, 'INSUFFICIENT_EVIDENCE' => .10,
        'COMPLEX_CASE' => .06, 'CONFLICTING_EVIDENCE' => .07, 'OUT_OF_SCOPE' => .05, 'FAILED' => .04,
    ];

    /** Sample questions per state, taken from the design's demo content. */
    private const SAMPLES = [
        'ANSWERABLE' => ['هل ينقض خروج الريح الوضوء؟', 'صليت الظهر خمس ركعات ناسياً، ماذا أفعل؟', 'أمي كبيرة في السن ولا تستطيع الصيام، ماذا عليها؟', 'هل يصح الوضوء مع وجود طلاء الأظافر؟', 'إذا صلى المسافر خلف إمام مقيم فهل يقصر أم يتم؟'],
        'NEEDS_CLARIFICATION' => ['هل يجوز الجمع؟', 'أنا مسافر، هل أقصر الصلاة؟', 'هل يجوز؟'],
        'INSUFFICIENT_EVIDENCE' => ['ما حكم التداول في العملات الرقمية المستقرة؟', 'هل الاستثمار في صناديق المؤشرات المتداولة حلال؟', 'ما حكم البطاقة الائتمانية مع السداد في فترة السماح؟'],
        'COMPLEX_CASE' => ['توفيت جدتي وتركت ذهباً وأرضاً، كيف نقسمها؟', 'زوجي حلف بالطلاق إن خرجتُ من البيت، وخرجت. هل وقع الطلاق؟'],
        'CONFLICTING_EVIDENCE' => ['هل تجب الزكاة في الذهب الذي تلبسه زوجتي؟', 'هل يجوز إخراج زكاة الفطر نقداً؟'],
        'OUT_OF_SCOPE' => ['ما أفضل جوال للتصوير بسعر متوسط؟', 'ما حالة الطقس غدًا في الرياض؟'],
        'FAILED' => ['ما حكم الأضحية عن الميت إذا لم يوصِ بها؟', 'هل يجوز الجمع بين صلاة الجمعة والعصر للمسافر؟'],
    ];

    /** The sections that are really indexed, so demo rows land where real ones would. */
    private const CHAPTERS = ['الفصل الأول: صلاة المسافر', 'الفصل الثاني: جمع الصلاة', 'الفصل الثالث: صلاة المريض', 'الفصل الرابع: صلاة الخوف'];

    public function handle(): int
    {
        if ($this->option('purge')) {
            $deleted = Question::where('is_demo', true)->delete();
            $this->components->info("Deleted {$deleted} demo questions.");

            return self::SUCCESS;
        }

        if ($this->option('if-missing') && Question::where('is_demo', true)->exists()) {
            $this->components->info('Demo questions already exist; nothing to do.');

            return self::SUCCESS;
        }

        $days = max(1, (int) $this->option('days'));
        $perDay = max(1, (int) $this->option('per-day'));
        $today = CarbonImmutable::today();
        $rows = [];

        for ($d = $days - 1; $d >= 0; $d--) {
            $date = $today->subDays($d);
            // Gentle growth over time, busier on Fridays and Saturdays.
            $volume = (int) round($perDay * (0.75 + 0.5 * ($days - $d) / $days) * (in_array($date->dayOfWeek, [5, 6], true) ? 1.25 : 1) * (0.85 + mt_rand() / mt_getrandmax() * 0.3));

            for ($i = 0; $i < $volume; $i++) {
                $state = $this->pickState();
                $voice = mt_rand(1, 100) <= 32;
                $failed = $state === 'FAILED';
                $rated = ! $failed && mt_rand(1, 100) <= 22;
                $up = $rated && mt_rand(1, 100) <= ($state === 'ANSWERABLE' ? 88 : 70);
                $createdAt = $date->addSeconds(mt_rand(6 * 3600, 23 * 3600));

                $rows[] = [
                    'query' => self::SAMPLES[$state][array_rand(self::SAMPLES[$state])],
                    'language' => 'ar',
                    'answer_mode' => 'text',
                    'channel' => $voice ? Channel::Voice->value : Channel::Text->value,
                    'state' => $state,
                    'summary' => $state === 'ANSWERABLE' ? 'إجابة توضيحية لعرض لوحة الإدارة.' : null,
                    'escalation_message' => in_array($state, ['INSUFFICIENT_EVIDENCE', 'COMPLEX_CASE', 'CONFLICTING_EVIDENCE', 'OUT_OF_SCOPE'], true) ? 'رسالة توضيحية لعرض لوحة الإدارة.' : null,
                    'clarification_question' => $state === 'NEEDS_CLARIFICATION' ? 'سؤال توضيح لعرض اللوحة.' : null,
                    'citations' => json_encode([]),
                    'book' => $failed || in_array($state, ['OUT_OF_SCOPE', 'INSUFFICIENT_EVIDENCE'], true) ? null : 'كتاب الصلاة',
                    'chapter' => $failed || in_array($state, ['OUT_OF_SCOPE', 'INSUFFICIENT_EVIDENCE'], true) ? null : self::CHAPTERS[array_rand(self::CHAPTERS)],
                    'confidence' => $failed ? null : ($state === 'ANSWERABLE' ? mt_rand(55, 99) : mt_rand(0, 40)),
                    'model' => $failed ? null : 'demo-data',
                    'error_code' => $failed ? ['unreachable', 'upstream_error', 'invalid_response'][mt_rand(0, 2)] : null,
                    'error_message' => $failed ? 'خطأ توضيحي.' : null,
                    'duration_ms' => $failed ? null : (int) round(1000 * (2.2 + mt_rand() / mt_getrandmax() * 3.5) * ($voice ? 1.2 : 1)),
                    'feedback' => $rated ? ($up ? 'up' : 'down') : null,
                    'feedback_reason' => $rated && ! $up ? ['إجابة غير دقيقة', 'لم يفهم سؤالي', 'المصدر غير مناسب', 'الإجابة طويلة'][mt_rand(0, 3)] : null,
                    'feedback_at' => $rated ? $createdAt : null,
                    'visitor_id' => (string) Str::uuid(),
                    'is_demo' => true,
                    'created_at' => $createdAt,
                    'updated_at' => $createdAt,
                ];
            }
        }

        DB::transaction(function () use ($rows) {
            foreach (array_chunk($rows, 500) as $chunk) {
                Question::insert($chunk);
            }
        });

        $this->components->info('Created '.count($rows)." demo questions over {$days} days. Remove them with --purge.");

        return self::SUCCESS;
    }

    private function pickState(): string
    {
        $r = mt_rand() / mt_getrandmax();
        foreach (self::SHARES as $state => $share) {
            if (($r -= $share) <= 0) {
                return $state;
            }
        }

        return AnswerState::Answerable->value;
    }
}
