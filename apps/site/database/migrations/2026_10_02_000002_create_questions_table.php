<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('questions', function (Blueprint $table) {
            $table->id();

            // What the visitor asked.
            $table->text('query');
            $table->string('language', 16)->nullable();
            $table->string('answer_mode', 8)->default('text');

            // What came back. `state` is App\Enums\AnswerState.
            $table->string('state', 32)->index();
            $table->text('summary')->nullable();
            $table->text('explanation')->nullable();
            $table->text('clarification_question')->nullable();
            $table->text('escalation_message')->nullable();
            $table->jsonb('citations')->nullable();

            // Set only when state is FAILED.
            $table->string('error_code', 32)->nullable();
            $table->text('error_message')->nullable();

            $table->unsignedInteger('duration_ms')->nullable();

            // Anonymous activity tracking: visitors do not have accounts.
            $table->uuid('visitor_id')->nullable()->index();
            $table->string('ip_hash', 64)->nullable();
            $table->string('user_agent', 512)->nullable();

            $table->timestamps();
            $table->index('created_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('questions');
    }
};
