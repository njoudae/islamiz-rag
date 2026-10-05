<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('contact_messages', function (Blueprint $table) {
            // Optional: the question the visitor asked, pasted so the team can find the answer.
            $table->text('related_question')->nullable()->after('message');
            // The visitor asked for a copy of the message by email.
            $table->boolean('send_copy')->default(false)->after('related_question');
        });
    }

    public function down(): void
    {
        Schema::table('contact_messages', function (Blueprint $table) {
            $table->dropColumn(['related_question', 'send_copy']);
        });
    }
};
