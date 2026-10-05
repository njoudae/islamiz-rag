<?php

namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Http\Requests\Auth\LoginRequest;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Inertia\Inertia;
use Inertia\Response;

class AuthenticatedSessionController extends Controller
{
    public function create(Request $request): Response
    {
        return Inertia::render('auth/Login', [
            // Set when a guest was bounced here from an admin page.
            'fromAdmin' => str_starts_with((string) $request->session()->get('url.intended'), url('/admin')),
            'demoCredentials' => config('daleel.admin.show_credentials') ? [
                'email' => config('daleel.admin.email'),
                'password' => config('daleel.admin.password'),
            ] : null,
        ]);
    }

    public function store(LoginRequest $request): RedirectResponse
    {
        $request->authenticate();

        $request->session()->regenerate();

        $name = (string) $request->user()->name;

        return redirect()->intended(route('admin.dashboard'))
            ->with('toast', 'مرحباً '.strtok($name, ' ').'.');
    }

    public function destroy(Request $request): RedirectResponse
    {
        Auth::guard('web')->logout();

        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect()->route('home')->with('toast', 'سُجّل خروجك.');
    }
}
