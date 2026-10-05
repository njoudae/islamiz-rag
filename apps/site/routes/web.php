<?php

use App\Http\Controllers\Admin\GapsController;
use App\Http\Controllers\Admin\MessageController;
use App\Http\Controllers\Admin\OverviewController;
use App\Http\Controllers\Admin\QualityController;
use App\Http\Controllers\Admin\ReviewController;
use App\Http\Controllers\Auth\AuthenticatedSessionController;
use App\Http\Controllers\ContactController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

// Public pages. Visitors never log in.
Route::inertia('/', 'public/Home')->name('home');
Route::inertia('/ask', 'public/Ask')->name('ask');
// The page used to live at /try; old links keep working, query string included.
Route::get('/try', fn (Request $request) => redirect()->route('ask', $request->query(), 301));
Route::inertia('/encyclopedia', 'public/Encyclopedia')->name('encyclopedia');
Route::get('/contact', [ContactController::class, 'create'])->name('contact');
Route::post('/contact', [ContactController::class, 'store'])->middleware('throttle:contact')->name('contact.store');

Route::middleware('guest')->group(function () {
    Route::get('login', [AuthenticatedSessionController::class, 'create'])->name('login');
    Route::post('login', [AuthenticatedSessionController::class, 'store'])->name('login.store');
});

Route::post('logout', [AuthenticatedSessionController::class, 'destroy'])
    ->middleware('auth')
    ->name('logout');

Route::middleware(['auth', 'admin'])->prefix('admin')->name('admin.')->group(function () {
    Route::get('/', OverviewController::class)->name('dashboard');
    Route::get('review', [ReviewController::class, 'index'])->name('review');
    Route::post('review/{question}', [ReviewController::class, 'store'])->name('review.store');
    Route::get('gaps', [GapsController::class, 'index'])->name('gaps');
    Route::post('gaps/tasks', [GapsController::class, 'storeTask'])->name('gaps.tasks.store');
    Route::patch('gaps/tasks/{task}', [GapsController::class, 'updateTask'])->name('gaps.tasks.update');
    Route::get('quality', [QualityController::class, 'index'])->name('quality');
    Route::get('quality/export', [QualityController::class, 'export'])->name('quality.export');
    Route::get('messages', [MessageController::class, 'index'])->name('messages');
    Route::patch('messages/{message}', [MessageController::class, 'update'])->name('messages.update');
});
