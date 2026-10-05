<?php

use App\Http\Controllers\Api\V1\AskController;
use App\Http\Controllers\Api\V1\FeedbackController;
use App\Http\Controllers\Api\V1\StatusController;
use Illuminate\Support\Facades\Route;

/*
| Public API used by the "try" page. No authentication: visitors use the
| tool without an account. Routes are prefixed with /api.
*/

Route::prefix('v1')->name('api.v1.')->group(function () {
    Route::get('status', StatusController::class)->name('status');
    Route::post('ask', AskController::class)->middleware('throttle:ask')->name('ask');
    Route::post('questions/{question}/feedback', FeedbackController::class)->middleware('throttle:ask')->name('feedback');
});
