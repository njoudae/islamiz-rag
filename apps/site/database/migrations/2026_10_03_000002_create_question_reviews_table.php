<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('question_reviews', function (Blueprint $table) {
            $table->id();
            $table->foreignId('question_id')->unique()->constrained()->cascadeOnDelete();
            $table->foreignId('reviewer_id')->nullable()->constrained('users')->nullOnDelete();

            // App\Enums\ReviewVerdict: was the answer correct, in need of an edit, or wrong.
            $table->string('verdict', 16);

            // App\Enums\AnswerState: the state the reviewer says was right. Compared with
            // questions.state to build the model-quality confusion matrix.
            $table->string('label', 32);

            $table->text('correction')->nullable();
            $table->boolean('add_to_eval')->default(true);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('question_reviews');
    }
};
