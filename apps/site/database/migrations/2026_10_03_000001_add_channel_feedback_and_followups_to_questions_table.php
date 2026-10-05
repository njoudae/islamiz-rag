<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('questions', function (Blueprint $table) {
            // A follow-up, such as the reply to a clarifying question, points at the question it continues.
            $table->foreignId('parent_id')->nullable()->after('id')->constrained('questions')->nullOnDelete();

            // How the visitor asked: typed, or spoken and transcribed in the browser.
            $table->string('channel', 8)->default('text')->after('answer_mode')->index();

            // The visitor's thumbs up or down, and the reason picked after a thumbs down.
            $table->string('feedback', 8)->nullable()->after('duration_ms');
            $table->string('feedback_reason', 100)->nullable()->after('feedback');
            $table->timestamp('feedback_at')->nullable()->after('feedback_reason');

            // Rows created by `php artisan daleel:demo-data`, so they can be labelled and purged.
            $table->boolean('is_demo')->default(false)->after('user_agent')->index();
        });
    }

    public function down(): void
    {
        Schema::table('questions', function (Blueprint $table) {
            $table->dropConstrainedForeignId('parent_id');
            $table->dropIndex(['channel']);
            $table->dropIndex(['is_demo']);
            $table->dropColumn(['channel', 'feedback', 'feedback_reason', 'feedback_at', 'is_demo']);
        });
    }
};
