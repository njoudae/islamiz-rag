<?php

namespace Tests\Feature;

use App\Enums\AnswerState;
use App\Models\Question;
use App\Models\QuestionReview;
use App\Models\User;
use Database\Seeders\AdminUserSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

class AdminAreaTest extends TestCase
{
    use RefreshDatabase;

    private function admin(): User
    {
        $this->seed(AdminUserSeeder::class);

        return User::where('email', config('daleel.admin.email'))->sole();
    }

    public function test_public_pages_render_without_login(): void
    {
        $this->get('/')->assertOk()->assertInertia(fn (Assert $page) => $page->component('public/Home'));
        $this->get('/ask')->assertOk()->assertInertia(fn (Assert $page) => $page->component('public/Ask'));
        // The page's previous address still works.
        $this->get('/try?q=سؤال')->assertRedirect('/ask?q='.rawurlencode('سؤال'));
        $this->get('/encyclopedia')->assertOk()->assertInertia(fn (Assert $page) => $page->component('public/Encyclopedia'));
        $this->get('/contact')->assertOk()->assertInertia(fn (Assert $page) => $page->component('public/Contact'));
    }

    public function test_guests_are_sent_to_the_login_page(): void
    {
        foreach (['/admin', '/admin/review', '/admin/gaps', '/admin/quality', '/admin/quality/export', '/admin/messages'] as $url) {
            $this->get($url)->assertRedirect('/login');
        }

        $this->get('/login')->assertOk()->assertInertia(fn (Assert $page) => $page
            ->component('auth/Login')
            ->where('demoCredentials.email', config('daleel.admin.email')));
    }

    public function test_the_demo_credentials_box_can_be_turned_off(): void
    {
        config(['daleel.admin.show_credentials' => false]);

        $this->get('/login')->assertInertia(fn (Assert $page) => $page->where('demoCredentials', null));
    }

    public function test_the_seeded_admin_can_log_in_and_out(): void
    {
        $this->admin();

        $this->post('/login', [
            'email' => config('daleel.admin.email'),
            'password' => config('daleel.admin.password'),
        ])->assertRedirect('/admin')->assertSessionHas('toast');

        $this->assertAuthenticated();

        $this->post('/logout')->assertRedirect('/');
        $this->assertGuest();
    }

    public function test_wrong_credentials_are_rejected_and_throttled(): void
    {
        $this->admin();

        foreach (range(1, 5) as $attempt) {
            $this->post('/login', ['email' => config('daleel.admin.email'), 'password' => 'wrong'])
                ->assertSessionHasErrors('email');
        }

        // The sixth attempt is locked out even with the right password.
        $this->post('/login', ['email' => config('daleel.admin.email'), 'password' => config('daleel.admin.password')])
            ->assertSessionHasErrors('email');

        $this->assertGuest();
    }

    public function test_seeding_twice_keeps_a_single_admin_in_sync_with_configuration(): void
    {
        $this->admin();
        config(['daleel.admin.password' => 'rotated-password']);
        $this->seed(AdminUserSeeder::class);

        $this->assertSame(1, User::count());
        $this->post('/login', ['email' => config('daleel.admin.email'), 'password' => 'rotated-password'])->assertRedirect('/admin');
    }

    public function test_changing_the_admin_address_renames_the_account_instead_of_adding_one(): void
    {
        $this->admin();
        $old = config('daleel.admin.email');
        config(['daleel.admin.email' => 'new-admin@daleel.sa']);
        $this->seed(AdminUserSeeder::class);

        $this->assertSame(['new-admin@daleel.sa'], User::pluck('email')->all());
        $this->post('/login', ['email' => $old, 'password' => config('daleel.admin.password')])->assertSessionHasErrors('email');
    }

    public function test_non_admin_accounts_cannot_open_the_admin_area(): void
    {
        $this->actingAs(User::factory()->create())->get('/admin')->assertForbidden();
    }

    public function test_the_overview_returns_two_windows_of_daily_rows(): void
    {
        Question::factory()->count(3)->create();
        Question::factory()->withOutcome(AnswerState::Failed)->voice()->create();
        Question::factory()->create(['created_at' => now()->subDays(10)]);
        Question::factory()->create(['created_at' => now()->subDays(40)]); // outside both 7-day windows

        $this->actingAs($this->admin())->get('/admin?period=7')->assertOk()->assertInertia(fn (Assert $page) => $page
            ->component('admin/Overview')
            ->where('period', 7)
            ->has('days', 14)
            ->where('days.13.total', 4)
            ->where('days.13.voice', 1)
            ->where('days.13.voiceFailed', 1)
            ->where('days.13.c.ANSWERABLE', 3)
            ->where('days.3.total', 1)
            ->has('recent', 6)
            ->has('messages', 0)
            ->where('hasDemoData', false)
            ->where('knowledge.documents', 40)
            ->where('knowledge.books.0.title', 'كتاب الصلاة')
            ->where('knowledge.models.generation', 'test-model')
            ->where('pendingReviews', 6));
    }

    public function test_the_overview_rejects_unknown_periods(): void
    {
        $this->actingAs($this->admin())->get('/admin?period=12')->assertSessionHasErrors('period');
    }

    public function test_the_review_queue_filters_on_the_server(): void
    {
        $admin = $this->admin();
        $reviewed = Question::factory()->create(['query' => 'سؤال تمت مراجعته']);
        $reviewed->review()->create(['verdict' => 'correct', 'label' => 'ANSWERABLE'])->reviewer()->associate($admin)->save();
        Question::factory()->withOutcome(AnswerState::OutOfScope)->create(['query' => 'ما حالة الطقس غدًا؟']);
        Question::factory()->withOutcome(AnswerState::Failed)->voice()->create();

        $this->actingAs($admin)->get('/admin/review')->assertInertia(fn (Assert $page) => $page
            ->component('admin/Review')
            ->has('questions.data', 2)
            ->where('tabCounts', ['pending' => 2, 'done' => 1, 'all' => 3])
            ->where('kpis.pending', 2));

        $this->actingAs($admin)->get('/admin/review?filter=done')->assertInertia(fn (Assert $page) => $page
            ->has('questions.data', 1)
            ->where('questions.data.0.review.verdict', 'correct'));

        $this->actingAs($admin)->get('/admin/review?filter=all&state=OUT_OF_SCOPE')->assertInertia(fn (Assert $page) => $page
            ->has('questions.data', 1)
            ->where('questions.data.0.reason', 'فجوة معرفية'));

        $this->actingAs($admin)->get('/admin/review?filter=all&channel=voice')->assertInertia(fn (Assert $page) => $page
            ->has('questions.data', 1)
            ->where('questions.data.0.state', 'FAILED'));

        $this->actingAs($admin)->get('/admin/review?filter=all&search='.urlencode('الطقس'))->assertInertia(fn (Assert $page) => $page
            ->has('questions.data', 1));

        $this->actingAs($admin)->get('/admin/review?state=NOPE')->assertSessionHasErrors('state');
    }

    public function test_a_review_is_saved_and_can_be_updated(): void
    {
        $admin = $this->admin();
        $question = Question::factory()->create();

        $this->actingAs($admin)->post("/admin/review/{$question->id}", [])->assertSessionHasErrors('verdict');

        $this->actingAs($admin)
            ->post("/admin/review/{$question->id}", ['verdict' => 'wrong', 'label' => 'CONFLICTING_EVIDENCE', 'correction' => 'المسألة خلافية.', 'add_to_eval' => true])
            ->assertSessionHas('toast', 'حُفظت المراجعة، وسُجّل التصحيح إلى «أدلة متعارضة».');

        $this->actingAs($admin)
            ->post("/admin/review/{$question->id}", ['verdict' => 'edit', 'label' => 'ANSWERABLE', 'add_to_eval' => false])
            ->assertSessionHas('toast', 'حُفظت المراجعة.');

        $review = QuestionReview::sole();
        $this->assertSame('edit', $review->verdict->value);
        $this->assertSame(AnswerState::Answerable, $review->label);
        $this->assertFalse($review->add_to_eval);
        $this->assertSame($admin->id, $review->reviewer_id);
    }

    public function test_the_quality_page_builds_the_confusion_matrix_from_reviews(): void
    {
        $admin = $this->admin();
        $right = Question::factory()->create();
        $right->review()->create(['verdict' => 'correct', 'label' => 'ANSWERABLE']);
        $wrong = Question::factory()->create();
        $wrong->review()->create(['verdict' => 'wrong', 'label' => 'CONFLICTING_EVIDENCE']);
        Question::factory()->withOutcome(AnswerState::Failed)->create(['error_code' => 'unreachable']);
        Question::factory()->create(['feedback' => 'down', 'feedback_reason' => 'لم يفهم سؤالي', 'feedback_at' => now()]);

        $this->actingAs($admin)->get('/admin/quality')->assertInertia(fn (Assert $page) => $page
            ->component('admin/Quality')
            ->has('pairs', 2)
            ->where('failedTotal', 1)
            ->where('failures.0.label', 'تعذّر الوصول إلى خدمة الذكاء الاصطناعي')
            ->where('feedbackReasons.0.label', 'لم يفهم سؤالي')
            ->where('reviewed', 2)
            ->where('evalSize', 2));
    }

    public function test_the_evaluation_set_downloads_as_json(): void
    {
        $question = Question::factory()->create(['query' => 'سؤال للتقييم']);
        $question->review()->create(['verdict' => 'wrong', 'label' => 'COMPLEX_CASE', 'correction' => 'يحال إلى مختص.']);
        Question::factory()->create()->review()->create(['verdict' => 'correct', 'label' => 'ANSWERABLE', 'add_to_eval' => false]);

        $response = $this->actingAs($this->admin())->get('/admin/quality/export');

        $response->assertOk()->assertDownload('daleel-eval-set.json');
        $rows = json_decode($response->streamedContent(), true);
        $this->assertCount(1, $rows);
        $this->assertSame(['question' => 'سؤال للتقييم', 'predicted_status' => 'ANSWERABLE', 'gold_status' => 'COMPLEX_CASE'], array_intersect_key($rows[0], array_flip(['question', 'predicted_status', 'gold_status'])));
    }
}
