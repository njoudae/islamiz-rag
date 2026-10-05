<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Follow-up tasks the team opens from the knowledge-gaps page.
        Schema::create('gap_tasks', function (Blueprint $table) {
            $table->id();
            // Stable identifier of the gap group the task was opened for.
            $table->string('group_key', 64)->unique();
            $table->string('kind', 32);
            $table->string('title', 300);
            $table->string('status', 16)->default('open')->index();
            $table->foreignId('created_by')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('gap_tasks');
    }
};
