<?php

namespace Tests\Feature;

use App\Enums\ContactStatus;
use App\Enums\ContactTopic;
use App\Mail\ContactMessageCopy;
use App\Models\ContactMessage;
use App\Models\User;
use Database\Seeders\AdminUserSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Mail;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

class ContactTest extends TestCase
{
    use RefreshDatabase;

    private function valid(array $overrides = []): array
    {
        return [
            'name' => 'عبدالله',
            'email' => 'visitor@example.com',
            'topic' => 'answer_feedback',
            'message' => 'إجابة سؤال قصر الصلاة لم تذكر مدة الإقامة.',
            ...$overrides,
        ];
    }

    private function admin(): User
    {
        $this->seed(AdminUserSeeder::class);

        return User::where('email', config('daleel.admin.email'))->sole();
    }

    public function test_the_contact_page_lists_the_topics(): void
    {
        $this->get('/contact')->assertOk()->assertInertia(fn (Assert $page) => $page
            ->component('public/Contact')
            ->has('topics', count(ContactTopic::cases()))
            ->where('topics.0.label', 'الإبلاغ عن خطأ في إجابة')
            ->where('contactEmail', config('daleel.contact_email'))
            ->where('messageMax', 1500));
    }

    public function test_a_message_is_stored_as_new(): void
    {
        Mail::fake();

        $this->from('/contact')->post('/contact', $this->valid(['visitor_id' => '7b0a9a0e-6f0e-4d5c-9a43-0d2f3b8f1c11', 'related_question' => 'أنا مسافر، هل أقصر الصلاة؟']))
            ->assertRedirect('/contact')
            ->assertSessionHas('contactSent', true);

        $message = ContactMessage::sole();
        $this->assertSame('عبدالله', $message->name);
        $this->assertSame(ContactTopic::AnswerFeedback, $message->topic);
        $this->assertSame(ContactStatus::New, $message->status);
        $this->assertNull($message->read_at);
        $this->assertNotNull($message->ip_hash);
        $this->assertSame('7b0a9a0e-6f0e-4d5c-9a43-0d2f3b8f1c11', $message->visitor_id);
        $this->assertSame('أنا مسافر، هل أقصر الصلاة؟', $message->related_question);
        $this->assertFalse($message->send_copy);
        Mail::assertNothingSent();
    }

    public function test_a_copy_is_emailed_when_asked_for(): void
    {
        Mail::fake();

        $this->post('/contact', $this->valid(['send_copy' => true]))->assertSessionHas('contactSent', true);

        $message = ContactMessage::sole();
        $this->assertTrue($message->send_copy);
        Mail::assertSent(ContactMessageCopy::class, fn (ContactMessageCopy $mail) => $mail->hasTo('visitor@example.com')
            && $mail->contactMessage->is($message));
    }

    public function test_a_mail_failure_does_not_lose_the_message(): void
    {
        Mail::shouldReceive('to')->andThrow(new \RuntimeException('SMTP down'));

        $this->post('/contact', $this->valid(['send_copy' => true]))->assertSessionHas('contactSent', true);

        $this->assertSame(1, ContactMessage::count());
    }

    public function test_messages_longer_than_the_limit_are_rejected(): void
    {
        $this->post('/contact', $this->valid(['message' => str_repeat('م', 1501)]))
            ->assertSessionHasErrors(['message' => 'الرسالة طويلة جداً. اختصرها إلى 1500 حرف.']);
    }

    public function test_invalid_messages_are_rejected_with_arabic_errors(): void
    {
        $this->post('/contact', $this->valid(['name' => '', 'email' => 'not-an-email', 'topic' => 'spam', 'message' => 'قصيرة']))
            ->assertSessionHasErrors([
                'name' => 'اكتب اسمك.',
                'email' => 'صيغة البريد غير صحيحة، مثل name@example.com.',
                'topic' => 'اختر موضوعاً من القائمة.',
                'message' => 'الرسالة قصيرة جداً. اكتب عشرة أحرف على الأقل.',
            ]);

        $this->assertSame(0, ContactMessage::count());
    }

    public function test_bots_filling_the_honeypot_are_told_it_worked_but_nothing_is_stored(): void
    {
        $this->post('/contact', $this->valid(['website' => 'https://spam.example']))->assertSessionHas('contactSent', true);

        $this->assertSame(0, ContactMessage::count());
    }

    public function test_the_form_is_rate_limited(): void
    {
        foreach (range(1, 5) as $i) {
            $this->post('/contact', $this->valid())->assertRedirect();
        }

        $this->post('/contact', $this->valid())->assertTooManyRequests();
        $this->assertSame(5, ContactMessage::count());
    }

    public function test_the_inbox_is_for_admins_only(): void
    {
        $message = ContactMessage::factory()->create();

        $this->get('/admin/messages')->assertRedirect('/login');
        $this->patch("/admin/messages/{$message->id}", ['status' => 'read'])->assertRedirect('/login');
        $this->actingAs(User::factory()->create())->get('/admin/messages')->assertForbidden();
    }

    public function test_the_inbox_shows_new_messages_first_and_counts_each_status(): void
    {
        ContactMessage::factory()->count(2)->create();
        ContactMessage::factory()->create(['message' => 'رسالة عن مشكلة في الصوت'])->markAs(ContactStatus::Read);
        ContactMessage::factory()->create()->markAs(ContactStatus::Archived);
        $admin = $this->admin();

        $this->actingAs($admin)->get('/admin/messages')->assertInertia(fn (Assert $page) => $page
            ->component('admin/Messages')
            ->where('filters.status', 'new')
            ->has('messages.data', 2)
            ->where('counts', ['new' => 2, 'read' => 1, 'archived' => 1, 'all' => 4])
            ->where('newMessages', 2));

        // The dashboard itself lists the newest messages and how many are unread.
        $this->actingAs($admin)->get('/admin')->assertInertia(fn (Assert $page) => $page
            ->has('messages', 4)
            ->where('messages.0.topic_label', 'استفسار عام')
            ->where('newMessages', 2));

        $this->actingAs($admin)->get('/admin/messages?status=all&search='.urlencode('الصوت'))->assertInertia(fn (Assert $page) => $page
            ->has('messages.data', 1)
            ->where('messages.data.0.status', 'read'));

        $this->actingAs($admin)->get('/admin/messages?status=nope')->assertSessionHasErrors('status');
    }

    public function test_admins_can_read_archive_and_mark_unread(): void
    {
        $message = ContactMessage::factory()->create();
        $admin = $this->admin();

        $this->actingAs($admin)->patch("/admin/messages/{$message->id}", ['status' => 'read'])->assertRedirect();
        $message->refresh();
        $this->assertSame(ContactStatus::Read, $message->status);
        $readAt = $message->read_at;
        $this->assertNotNull($readAt);

        $this->actingAs($admin)->patch("/admin/messages/{$message->id}", ['status' => 'archived']);
        $message->refresh();
        $this->assertSame(ContactStatus::Archived, $message->status);
        $this->assertTrue($readAt->equalTo($message->read_at), 'archiving keeps the first read time');

        $this->actingAs($admin)->patch("/admin/messages/{$message->id}", ['status' => 'new']);
        $this->assertNull($message->refresh()->read_at);

        $this->actingAs($admin)->patch("/admin/messages/{$message->id}", ['status' => 'deleted'])->assertSessionHasErrors('status');
    }
}
