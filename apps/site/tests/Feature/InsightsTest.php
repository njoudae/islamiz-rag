<?php

namespace Tests\Feature;

use App\Enums\AnswerState;
use App\Models\GapTask;
use App\Models\Question;
use App\Models\User;
use App\Services\Ai\KnowledgeBase;
use Database\Seeders\AdminUserSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

/**
 * The admin figures that replaced demo content: they must come from the
 * question log, the reviews and what the AI service reports.
 */
class InsightsTest extends TestCase
{
    use RefreshDatabase;

    private const TRAVEL = 'الفصل الأول: صلاة المسافر';

    private function admin(): User
    {
        $this->seed(AdminUserSeeder::class);

        return User::where('email', config('daleel.admin.email'))->sole();
    }

    private function aiAnswers(array $payload): void
    {
        config(['services.ai.base_url' => 'http://ai.test']);
        Http::fake(['ai.test/v1/ask' => Http::response(['language' => 'ar', 'citations' => [], ...$payload])]);
    }

    public function test_an_answered_question_records_its_section_score_model_and_reason(): void
    {
        $path = ['كِتابُ الصَّلاةِ', 'البابُ العاشِرُ: صلاةُ أهلِ الأَعذارِ', 'الفَصْلُ الأَوَّل: صلاةُ المُسافِر', 'المَبحثُ الثالث'];
        $this->aiAnswers([
            'state' => 'ANSWERABLE',
            'summary' => 'يقصر',
            'citations' => [['fatwa_id' => 1455, 'title' => 't', 'source_url' => 'https://dorar.net/feqhia/1455', 'category_path' => $path]],
            'related' => [['fatwa_id' => 1455, 'title' => 't', 'source_url' => 'https://dorar.net/feqhia/1455', 'category_path' => $path, 'reranker_score' => 0.93]],
            'evidence_score' => 0.93,
            'reasons' => ['direct source coverage', 'strong reranker score'],
            'model' => 'gpt-test',
        ]);

        $this->postJson('/api/v1/ask', ['query' => 'أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟'])->assertOk();

        $question = Question::sole();
        $this->assertSame('كتاب الصلاة', $question->book);
        $this->assertSame(self::TRAVEL, $question->chapter);
        $this->assertSame(93, $question->confidence);
        $this->assertSame('gpt-test', $question->model);
        $this->assertSame('direct source coverage; strong reranker score', $question->state_reason);
        $this->assertSame(1455, $question->related[0]['fatwa_id']);
    }

    public function test_a_refusal_is_not_tied_to_a_section_when_nothing_indexed_is_close(): void
    {
        $this->aiAnswers([
            'state' => 'INSUFFICIENT_EVIDENCE',
            'escalation_message' => 'لا دليل كافٍ',
            'related' => [['fatwa_id' => 9, 'title' => 't', 'source_url' => 'https://dorar.net/feqhia/9', 'category_path' => ['كتاب الصلاة', 'باب', 'الفصل الثاني: جمع الصلاة'], 'reranker_score' => 0.00001]],
            'evidence_score' => 0.00001,
        ]);

        $this->postJson('/api/v1/ask', ['query' => 'ما حكم تداول العملات الرقمية الجديدة؟'])->assertOk();

        $question = Question::sole();
        $this->assertNull($question->book);
        $this->assertNull($question->chapter);
        $this->assertSame(0, $question->confidence);
    }

    public function test_an_older_ai_service_without_the_new_fields_still_works(): void
    {
        $this->aiAnswers(['state' => 'OUT_OF_SCOPE', 'escalation_message' => 'خارج النطاق']);

        $this->postJson('/api/v1/ask', ['query' => 'ما حالة الطقس غدًا؟'])->assertOk();

        $question = Question::sole();
        $this->assertNull($question->confidence);
        $this->assertNull($question->model);
        $this->assertSame([], $question->related);
    }

    public function test_knowledge_gaps_are_grouped_from_real_questions_with_change_and_tasks(): void
    {
        // Current window: two uncovered questions, one near the travel section, a repeated off-topic question.
        Question::factory()->withOutcome(AnswerState::InsufficientEvidence)->count(2)->create(['query' => 'ما حكم العملات الرقمية؟']);
        Question::factory()->withOutcome(AnswerState::InsufficientEvidence)->create(['book' => 'كتاب الصلاة', 'chapter' => self::TRAVEL, 'query' => 'هل يقصر الطيار؟']);
        Question::factory()->withOutcome(AnswerState::OutOfScope)->create(['query' => 'ما حالة الطقس غدًا؟']);
        Question::factory()->withOutcome(AnswerState::OutOfScope)->create(['query' => 'ما حالةُ الطقس غداً']);
        // Previous window: one uncovered question, so the bucket doubled.
        Question::factory()->withOutcome(AnswerState::InsufficientEvidence)->create(['created_at' => now()->subDays(10)]);
        // Answered questions feed the coverage table.
        Question::factory()->count(3)->create(['book' => 'كتاب الصلاة', 'chapter' => self::TRAVEL]);

        $admin = $this->admin();

        $this->actingAs($admin)->get('/admin/gaps?period=7')->assertOk()->assertInertia(fn (Assert $page) => $page
            ->component('admin/Gaps')
            ->has('insufficient', 2)
            ->where('insufficient.0.title', 'مسائل لا يغطيها الفهرس الحالي')
            ->where('insufficient.0.n', 2)
            ->where('insufficient.0.previous', 1)
            ->where('insufficient.0.delta', 100)
            ->where('insufficient.0.examples', ['ما حكم العملات الرقمية؟'])
            ->where('insufficient.0.task', null)
            ->where('insufficient.1.title', self::TRAVEL)
            ->where('insufficient.1.book', 'كتاب الصلاة')
            ->where('insufficient.1.delta', null)
            ->has('outOfScope', 1)
            ->where('outOfScope.0.n', 2)
            ->has('sections', 1)
            ->where('sections.0', ['book' => 'كتاب الصلاة', 'chapter' => self::TRAVEL, 'total' => 4, 'answered' => 3, 'insufficient' => 1])
            ->where('openTasks', 0));
    }

    public function test_a_gap_task_is_stored_closed_and_reopened(): void
    {
        $admin = $this->admin();
        $key = str_repeat('a', 40);

        $this->actingAs($admin)->post('/admin/gaps/tasks', ['group_key' => $key, 'kind' => 'insufficient', 'title' => 'العملات الرقمية'])
            ->assertSessionHas('toast');
        $this->actingAs($admin)->post('/admin/gaps/tasks', ['group_key' => $key, 'kind' => 'insufficient', 'title' => 'العملات الرقمية']);

        $task = GapTask::sole();
        $this->assertSame('open', $task->status);
        $this->assertSame($admin->id, $task->created_by);

        $this->actingAs($admin)->patch("/admin/gaps/tasks/{$task->id}", ['status' => 'done']);
        $this->assertSame('done', $task->refresh()->status);
        $this->assertNotNull($task->completed_at);

        $this->actingAs($admin)->patch("/admin/gaps/tasks/{$task->id}", ['status' => 'open']);
        $this->assertNull($task->refresh()->completed_at);

        $this->actingAs($admin)->post('/admin/gaps/tasks', ['group_key' => 'short', 'kind' => 'other', 'title' => ''])
            ->assertSessionHasErrors(['group_key', 'kind', 'title']);
        $this->post('/logout');
        $this->post('/admin/gaps/tasks', ['group_key' => $key, 'kind' => 'insufficient', 'title' => 'x'])->assertRedirect('/login');
    }

    public function test_quality_figures_come_from_reviews_per_model(): void
    {
        $admin = $this->admin();

        // Old model: one answer, reviewed as wrongly answered.
        $old = Question::factory()->create(['model' => 'gpt-old', 'duration_ms' => 9000, 'created_at' => now()->subDays(20)]);
        $old->review()->create(['verdict' => 'wrong', 'label' => 'NEEDS_CLARIFICATION', 'citation_correct' => false]);

        // New model: two correct answers with confirmed citations, one unjudged.
        foreach ([3000, 4000] as $ms) {
            Question::factory()->create(['model' => 'gpt-new', 'duration_ms' => $ms])
                ->review()->create(['verdict' => 'correct', 'label' => 'ANSWERABLE', 'citation_correct' => true]);
        }
        Question::factory()->create(['model' => 'gpt-new', 'duration_ms' => 5000])
            ->review()->create(['verdict' => 'correct', 'label' => 'ANSWERABLE']);

        $this->actingAs($admin)->get('/admin/quality')->assertInertia(fn (Assert $page) => $page
            ->where('citationAccuracy', ['value' => 0.6667, 'judged' => 3])
            ->has('versions', 2)
            ->where('versions.0.model', 'gpt-old')
            ->where('versions.0.accuracy', 0)
            ->where('versions.0.clarification', 0)
            ->where('versions.0.citation', 0)
            ->where('versions.0.p95', 9)
            ->where('versions.1.model', 'gpt-new')
            ->where('versions.1.questions', 3)
            ->where('versions.1.reviewed', 3)
            ->where('versions.1.accuracy', 100)
            ->where('versions.1.citation', 100)
            ->where('versions.1.referral', null)
            ->where('versions.1.p95', 5));
    }

    public function test_transcription_error_is_measured_from_reviewed_voice_questions(): void
    {
        $admin = $this->admin();

        // Heard "الظهر" where the visitor said "الظهار": one substitution in four words.
        Question::factory()->voice()->create(['query' => 'ما حكم الظهر شرعاً'])
            ->review()->create(['verdict' => 'wrong', 'label' => 'ANSWERABLE', 'transcript_correction' => 'ما حكم الظهار شرعاً']);
        // A voice question reviewed without touching the transcript counts as correctly heard.
        Question::factory()->voice()->create(['query' => 'هل يقصر المسافر الصلاة'])
            ->review()->create(['verdict' => 'correct', 'label' => 'ANSWERABLE']);
        // Typed questions never count.
        Question::factory()->create()->review()->create(['verdict' => 'correct', 'label' => 'ANSWERABLE', 'transcript_correction' => 'نص آخر تماماً']);

        $this->actingAs($admin)->get('/admin/quality')->assertInertia(fn (Assert $page) => $page
            ->where('transcription.samples', 2)
            ->where('transcription.wer', 0.125)
            ->where('transcription.terms', [['right' => 'الظهار', 'wrong' => 'الظهر', 'n' => 1]]));

        $this->actingAs($admin)->get('/admin')->assertInertia(fn (Assert $page) => $page->where('transcription.wer', 0.125));
    }

    public function test_the_trend_chart_marks_model_changes_and_outage_days(): void
    {
        Question::factory()->create(['model' => 'gpt-old', 'created_at' => now()->subDays(5)]);
        Question::factory()->count(2)->create(['model' => 'gpt-new', 'created_at' => now()->subDays(2)]);
        // Yesterday: three of four questions failed.
        Question::factory()->withOutcome(AnswerState::Failed)->count(3)->create(['created_at' => now()->subDay()]);
        Question::factory()->create(['model' => 'gpt-new', 'created_at' => now()->subDay()]);

        $this->actingAs($this->admin())->get('/admin?period=7')->assertInertia(fn (Assert $page) => $page
            ->where('events', [
                ['date' => now()->subDays(2)->toDateString(), 'label' => 'gpt-new'],
                ['date' => now()->subDay()->toDateString(), 'label' => 'تعطّل الخدمة'],
            ]));
    }

    public function test_the_review_queue_shows_confidence_and_stores_the_new_review_fields(): void
    {
        $admin = $this->admin();
        $weak = Question::factory()->voice()->create(['confidence' => 41, 'book' => 'كتاب الصلاة', 'chapter' => self::TRAVEL, 'state_reason' => 'direct source coverage']);
        Question::factory()->create(['confidence' => 96]);
        Question::factory()->withOutcome(AnswerState::InsufficientEvidence)->create(['confidence' => 2]); // a refusal, not a weak answer

        $this->actingAs($admin)->get('/admin/review')->assertInertia(fn (Assert $page) => $page
            ->where('kpis.lowConfidence', 1)
            ->where('questions.data.2.confidence', 41)
            ->where('questions.data.2.chapter', self::TRAVEL));

        $this->actingAs($admin)->post("/admin/review/{$weak->id}", [
            'verdict' => 'edit', 'label' => 'ANSWERABLE', 'citation_correct' => false, 'transcript_correction' => 'النص الصحيح للسؤال',
        ])->assertSessionHasNoErrors();

        $review = $weak->review()->sole();
        $this->assertFalse($review->citation_correct);
        $this->assertSame('النص الصحيح للسؤال', $review->transcript_correction);
    }

    public function test_the_index_summary_is_shared_and_survives_an_offline_ai_service(): void
    {
        $this->get('/')->assertInertia(fn (Assert $page) => $page
            ->where('knowledge.documents', 40)
            ->where('knowledge.chunks', 88)
            ->where('knowledge.books', [['title' => 'كتاب الصلاة', 'entries' => 40]])
            ->where('knowledge.chapters.0.title', self::TRAVEL));

        Cache::flush();
        $this->app->forgetInstance(KnowledgeBase::class);
        Http::swap(new Factory);
        Http::fake(['*' => Http::response('down', 503)]);

        $this->get('/')->assertOk()->assertInertia(fn (Assert $page) => $page->where('knowledge', null));
    }
}
