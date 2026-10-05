<?php

namespace Tests\Feature;

use App\Enums\Channel;
use App\Models\Question;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

/**
 * Follow-ups, voice questions, feedback and the live-mode status check.
 */
class VisitorApiTest extends TestCase
{
    use RefreshDatabase;

    private const VISITOR = '7b0a9a0e-6f0e-4d5c-9a43-0d2f3b8f1c11';

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.ai.base_url' => 'http://ai.test', 'services.ai.token' => 'secret-token']);
        Http::preventStrayRequests();
    }

    public function test_a_voice_question_is_recorded_with_its_channel(): void
    {
        Http::fake(['ai.test/v1/ask' => Http::response(['state' => 'OUT_OF_SCOPE', 'language' => 'ar', 'escalation_message' => 'خارج النطاق'])]);

        $this->postJson('/api/v1/ask', ['query' => 'ما حالة الطقس غدًا؟', 'channel' => 'voice'])->assertOk();

        $this->assertSame(Channel::Voice, Question::sole()->channel);
    }

    public function test_a_follow_up_is_sent_with_the_question_it_clarifies(): void
    {
        Http::fake(['ai.test/v1/ask' => Http::response(['state' => 'ANSWERABLE', 'language' => 'ar', 'summary' => 'يقصر', 'citations' => [['fatwa_id' => 1, 'title' => 't', 'source_url' => 'https://dorar.net/feqhia/1']]])]);
        $parent = Question::factory()->create(['query' => 'أنا مسافر، هل أقصر الصلاة؟', 'visitor_id' => self::VISITOR]);

        $this->postJson('/api/v1/ask', ['query' => 'سأقيم أربعة أيام', 'parent_id' => $parent->id], ['X-Visitor-Id' => self::VISITOR])->assertOk();

        Http::assertSent(fn (Request $r) => $r['query'] === "أنا مسافر، هل أقصر الصلاة؟\nسأقيم أربعة أيام");
        $child = Question::latest('id')->first();
        $this->assertSame($parent->id, $child->parent_id);
        $this->assertSame('سأقيم أربعة أيام', $child->query);
    }

    public function test_a_follow_up_cannot_borrow_another_visitors_question(): void
    {
        Http::fake(['ai.test/v1/ask' => Http::response(['state' => 'OUT_OF_SCOPE', 'language' => 'ar'])]);
        $parent = Question::factory()->create(['query' => 'سؤال زائر آخر', 'visitor_id' => fake()->uuid()]);

        $this->postJson('/api/v1/ask', ['query' => 'سأقيم أربعة أيام', 'parent_id' => $parent->id], ['X-Visitor-Id' => self::VISITOR])->assertOk();

        Http::assertSent(fn (Request $r) => $r['query'] === 'سأقيم أربعة أيام');
        $this->assertNull(Question::latest('id')->first()->parent_id);
    }

    public function test_the_asking_visitor_can_rate_an_answer(): void
    {
        $question = Question::factory()->create(['visitor_id' => self::VISITOR]);

        $this->postJson("/api/v1/questions/{$question->id}/feedback", ['value' => 'down', 'reason' => 'لم يفهم سؤالي'], ['X-Visitor-Id' => self::VISITOR])->assertNoContent();
        $question->refresh();
        $this->assertSame('down', $question->feedback);
        $this->assertSame('لم يفهم سؤالي', $question->feedback_reason);
        $this->assertNotNull($question->feedback_at);

        // Switching to thumbs up drops the reason; clearing removes the rating.
        $this->postJson("/api/v1/questions/{$question->id}/feedback", ['value' => 'up', 'reason' => 'ignored'], ['X-Visitor-Id' => self::VISITOR])->assertNoContent();
        $this->assertNull($question->refresh()->feedback_reason);
        $this->postJson("/api/v1/questions/{$question->id}/feedback", ['value' => null], ['X-Visitor-Id' => self::VISITOR])->assertNoContent();
        $this->assertNull($question->refresh()->feedback);
    }

    public function test_nobody_else_can_rate_an_answer(): void
    {
        $question = Question::factory()->create(['visitor_id' => self::VISITOR]);
        $anonymous = Question::factory()->create(['visitor_id' => null]);

        $this->postJson("/api/v1/questions/{$question->id}/feedback", ['value' => 'up'], ['X-Visitor-Id' => fake()->uuid()])->assertForbidden();
        $this->postJson("/api/v1/questions/{$question->id}/feedback", ['value' => 'up'])->assertForbidden();
        $this->postJson("/api/v1/questions/{$anonymous->id}/feedback", ['value' => 'up'], ['X-Visitor-Id' => self::VISITOR])->assertForbidden();
        $this->postJson("/api/v1/questions/{$question->id}/feedback", ['value' => 'meh'], ['X-Visitor-Id' => self::VISITOR])->assertJsonValidationErrors('value');

        $this->assertNull($question->refresh()->feedback);
    }

    public function test_the_status_endpoint_reports_whether_live_answers_are_available(): void
    {
        Http::fake(['ai.test/health' => Http::response(['status' => 'ok'])]);
        $this->getJson('/api/v1/status')->assertExactJson(['ai' => true]);
    }

    public function test_the_status_endpoint_reports_an_offline_ai_service(): void
    {
        Http::fake(['ai.test/health' => Http::response('down', 503)]);
        $this->getJson('/api/v1/status')->assertExactJson(['ai' => false]);
    }
}
