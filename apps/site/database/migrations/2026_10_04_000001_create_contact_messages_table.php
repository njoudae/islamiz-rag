<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('contact_messages', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->string('email', 190);
            // App\Enums\ContactTopic
            $table->string('topic', 32);
            $table->text('message');

            // App\Enums\ContactStatus: new until an admin opens it, then read, optionally archived.
            $table->string('status', 16)->default('new')->index();
            $table->timestamp('read_at')->nullable();

            // Same anonymous signals as the question log, for spotting abuse.
            $table->uuid('visitor_id')->nullable();
            $table->string('ip_hash', 64)->nullable();
            $table->string('user_agent', 512)->nullable();

            $table->timestamps();
            $table->index('created_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('contact_messages');
    }
};
