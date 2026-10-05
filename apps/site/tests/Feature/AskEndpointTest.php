<?php

namespace Tests\Feature;

use App\Enums\AnswerState;
use App\Models\Question;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class AskEndpointTest extends TestCase
{
    use RefreshDatabase;

    private const QUERY = 'أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟';

    protected function setUp(): void
    {
        parent::setUp();

        config([
            'services.ai.base_url' => 'http://ai.test',
            'services.ai.token' => 'secret-token',
        ]);

        Http::preventStrayRequests();
    }

    public function test_an_answer_is_returned_and_stored(): void
    {
        Http::fake(['ai.test/v1/ask' => Http::response([
            'state' => 'ANSWERABLE',
            'language' => 'ar',
            'summary' => 'ملخص مبني على المصدر',
            'explanation' => 'شرح',
            'clarification_question' => null,
            'escalation_message' => null,
            'citations' => [['fatwa_id' => 1455, 'title' => 'عدم نية الإقامة', 'source_url' => 'https://dorar.net/feqhia/1455/x']],
        ])]);

        $response = $this->postJson('/api/v1/ask', ['query' => self::QUERY, 'answer_mode' => 'text'], [
            'X-Visitor-Id' => '7b0a9a0e-6f0e-4d5c-9a43-0d2f3b8f1c11',
        ]);

        $response->assertOk()->assertJson([
            'state' => 'ANSWERABLE',
            'language' => 'ar',
            'summary' => 'ملخص مبني على المصدر',
            'citations' => [['fatwa_id' => 1455]],
        ]);

        $question = Question::sole();
        $this->assertSame(self::QUERY, $question->query);
        $this->assertSame(AnswerState::Answerable, $question->state);
        $this->assertSame('7b0a9a0e-6f0e-4d5c-9a43-0d2f3b8f1c11', $question->visitor_id);
        $this->assertSame(1455, $question->citations[0]['fatwa_id']);
        $this->assertNotNull($question->ip_hash);
        $this->assertNotSame('127.0.0.1', $question->ip_hash);
        $this->assertSame($question->id, $response->json('id'));

        Http::assertSent(fn (Request $request) => $request->url() === 'http://ai.test/v1/ask'
            && $request->hasHeader('X-Internal-Token', 'secret-token')
            && $request['query'] === self::QUERY
            && $request['answer_mode'] === 'text');
    }

    public function test_a_non_answer_state_is_passed_through_and_stored(): void
    {
        Http::fake(['ai.test/v1/ask' => Http::response([
            'state' => 'NEEDS_CLARIFICATION',
            'language' => 'ar',
            'clarification_question' => 'كم تنوي الإقامة في وجهتك؟',
            'citations' => [],
        ])]);

        $this->postJson('/api/v1/ask', ['query' => 'أنا مسافر، هل أقصر الصلاة؟'])
            ->assertOk()
            ->assertJson(['state' => 'NEEDS_CLARIFICATION', 'clarification_question' => 'كم تنوي الإقامة في وجهتك؟', 'summary' => null]);

        $this->assertSame(AnswerState::NeedsClarification, Question::sole()->state);
    }

    public function test_an_upstream_error_is_stored_as_failed_and_reported_as_bad_gateway(): void
    {
        Http::fake(['ai.test/v1/ask' => Http::response('Internal Server Error', 500)]);

        $this->postJson('/api/v1/ask', ['query' => self::QUERY])
            ->assertStatus(502)
            ->assertJson(['state' => 'FAILED', 'error' => 'upstream_error'])
            ->assertJsonMissingPath('summary');

        $question = Question::sole();
        $this->assertSame(AnswerState::Failed, $question->state);
        $this->assertSame('upstream_error', $question->error_code);
        $this->assertStringContainsString('500', $question->error_message);
    }

    public function test_an_unreachable_ai_service_is_reported_as_unavailable(): void
    {
        Http::fake(['ai.test/v1/ask' => fn () => throw new ConnectionException('Connection refused')]);

        $this->postJson('/api/v1/ask', ['query' => self::QUERY])
            ->assertStatus(503)
            ->assertJson(['state' => 'FAILED', 'error' => 'unreachable']);

        $this->assertSame('unreachable', Question::sole()->error_code);
    }

    public function test_an_unknown_state_from_the_ai_service_is_rejected(): void
    {
        Http::fake(['ai.test/v1/ask' => Http::response(['state' => 'SOMETHING_NEW', 'summary' => 'x'])]);

        $this->postJson('/api/v1/ask', ['query' => self::QUERY])
            ->assertStatus(502)
            ->assertJson(['error' => 'invalid_response']);

        $this->assertNull(Question::sole()->summary);
    }

    public function test_invalid_input_never_reaches_the_ai_service(): void
    {
        Http::fake();

        $this->postJson('/api/v1/ask', ['query' => 'ab'])->assertUnprocessable()->assertJsonValidationErrors('query');
        $this->postJson('/api/v1/ask', ['query' => self::QUERY, 'answer_mode' => 'fax'])->assertJsonValidationErrors('answer_mode');
        $this->postJson('/api/v1/ask', ['query' => self::QUERY], ['X-Visitor-Id' => 'not-a-uuid'])->assertJsonValidationErrors('visitor_id');

        Http::assertNothingSent();
        $this->assertSame(0, Question::count());
    }

    public function test_the_endpoint_is_rate_limited(): void
    {
        config(['daleel.ask.rate_limit_per_minute' => 2]);
        Http::fake(['ai.test/v1/ask' => Http::response(['state' => 'OUT_OF_SCOPE', 'language' => 'ar', 'escalation_message' => 'خارج النطاق'])]);

        $this->postJson('/api/v1/ask', ['query' => self::QUERY])->assertOk();
        $this->postJson('/api/v1/ask', ['query' => self::QUERY])->assertOk();
        $this->postJson('/api/v1/ask', ['query' => self::QUERY])->assertTooManyRequests();
    }

    public function test_cross_origin_browsers_are_not_allowed_by_default(): void
    {
        // The visitor pages are same-origin, so no foreign origin is ever echoed back.
        $response = $this->withHeaders(['Origin' => 'https://evil.example', 'Access-Control-Request-Method' => 'POST'])
            ->options('/api/v1/ask');

        $this->assertNotSame('https://evil.example', $response->headers->get('Access-Control-Allow-Origin'));
        $this->assertNotSame('*', $response->headers->get('Access-Control-Allow-Origin'));
    }
}
