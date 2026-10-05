<?php

namespace App\Http\Controllers;

use App\Enums\ContactTopic;
use App\Http\Requests\ContactRequest;
use App\Mail\ContactMessageCopy;
use App\Models\ContactMessage;
use Illuminate\Http\RedirectResponse;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

/**
 * The public "contact us" page. Messages are stored for the admin inbox.
 */
class ContactController extends Controller
{
    public function create(): Response
    {
        return Inertia::render('public/Contact', [
            'topics' => ContactTopic::options(),
            'contactEmail' => config('daleel.contact_email'),
            'messageMax' => ContactRequest::MESSAGE_MAX,
        ]);
    }

    public function store(ContactRequest $request): RedirectResponse
    {
        // Bots that fill the hidden field get the same answer as people, and nothing is stored.
        if ($request->isSpam()) {
            return back()->with('contactSent', true);
        }

        $message = ContactMessage::create([
            ...$request->safe()->only(['name', 'email', 'topic', 'related_question', 'message', 'visitor_id']),
            'send_copy' => $request->boolean('send_copy'),
            'ip_hash' => hash_hmac('sha256', (string) $request->ip(), (string) config('app.key')),
            'user_agent' => Str::limit((string) $request->userAgent(), 500, ''),
        ]);

        if ($message->send_copy) {
            // The message is already saved; a mail problem must not turn that into an error page.
            try {
                Mail::to($message->email)->send(new ContactMessageCopy($message));
            } catch (Throwable $exception) {
                report($exception);
            }
        }

        return back()->with('contactSent', true);
    }
}
