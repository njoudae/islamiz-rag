<?php

namespace App\Http\Middleware;

use App\Enums\ContactStatus;
use App\Models\ContactMessage;
use App\Models\Question;
use App\Services\Ai\KnowledgeBase;
use Illuminate\Http\Request;
use Inertia\Middleware;

class HandleInertiaRequests extends Middleware
{
    /**
     * The root template that's loaded on the first page visit.
     *
     * @var string
     */
    protected $rootView = 'app';

    /**
     * Props available to every page.
     *
     * @return array<string, mixed>
     */
    public function share(Request $request): array
    {
        $user = $request->user();

        return [
            ...parent::share($request),
            'auth' => [
                'user' => $user ? [
                    'name' => $user->name,
                    'email' => $user->email,
                    'role' => config('daleel.admin.role'),
                    'isAdmin' => (bool) $user->is_admin,
                ] : null,
            ],
            // Only evaluated for admins: the sidebar badge on the review queue.
            'pendingReviews' => fn () => $user?->is_admin ? Question::awaitingReview()->count() : null,
            'newMessages' => fn () => $user?->is_admin ? ContactMessage::where('status', ContactStatus::New)->count() : null,
            // True when synthetic questions were seeded: the admin header says so on every page.
            'hasDemoData' => fn () => $user?->is_admin ? Question::where('is_demo', true)->exists() : null,
            // What is really indexed and which models run, for the public pages and the admin sidebar.
            'knowledge' => fn () => app(KnowledgeBase::class)->summary(),
            'flash' => [
                'toast' => fn () => $request->session()->get('toast'),
                'contactSent' => fn () => (bool) $request->session()->get('contactSent'),
            ],
        ];
    }
}
