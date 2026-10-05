<?php

namespace App\Http\Controllers\Admin;

use App\Enums\ContactStatus;
use App\Http\Controllers\Controller;
use App\Models\ContactMessage;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

/**
 * The admin inbox for messages from the contact page.
 */
class MessageController extends Controller
{
    public function index(Request $request): Response
    {
        $filters = $request->validate([
            'status' => ['nullable', Rule::in(['new', 'read', 'archived', 'all'])],
            'search' => ['nullable', 'string', 'max:200'],
        ]);
        $status = $filters['status'] ?? 'new';
        $search = $filters['search'] ?? null;

        $base = fn (): Builder => ContactMessage::query()->when($search, fn (Builder $q, string $s) => $q->where(
            fn (Builder $w) => $w->whereLike('message', "%{$s}%")->orWhereLike('name', "%{$s}%")->orWhereLike('email', "%{$s}%"),
        ));

        $messages = $base()
            ->when($status !== 'all', fn (Builder $q) => $q->where('status', $status))
            ->latest()
            ->paginate(20)
            ->withQueryString()
            ->through(fn (ContactMessage $m) => [
                'id' => $m->id,
                'name' => $m->name,
                'email' => $m->email,
                'topic' => $m->topic->value,
                'topic_label' => $m->topic->label(),
                'message' => $m->message,
                'related_question' => $m->related_question,
                'send_copy' => $m->send_copy,
                'status' => $m->status->value,
                'created_at' => $m->created_at?->toIso8601String(),
                'read_at' => $m->read_at?->toIso8601String(),
            ]);

        $counts = $base()->toBase()->selectRaw('status, count(*) as n')->groupBy('status')->pluck('n', 'status');

        return Inertia::render('admin/Messages', [
            'messages' => $messages,
            'filters' => ['status' => $status, 'search' => $search],
            'counts' => [
                'new' => (int) ($counts['new'] ?? 0),
                'read' => (int) ($counts['read'] ?? 0),
                'archived' => (int) ($counts['archived'] ?? 0),
                'all' => (int) $counts->sum(),
            ],
        ]);
    }

    public function update(Request $request, ContactMessage $message): RedirectResponse
    {
        $data = $request->validate([
            'status' => ['required', Rule::enum(ContactStatus::class)],
        ]);

        $message->markAs(ContactStatus::from($data['status']));

        return back();
    }
}
