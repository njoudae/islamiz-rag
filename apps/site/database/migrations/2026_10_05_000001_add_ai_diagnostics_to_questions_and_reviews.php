<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('questions', function (Blueprint $table) {
            // Where the best-matching passage sits in the encyclopedia. Filled only when the
            // match is strong enough to mean something (see App\Actions\AskQuestion).
            $table->string('book', 200)->nullable()->after('citations')->index();
            $table->string('chapter', 300)->nullable()->after('book');

            // The passages the AI service considered, with their scores.
            $table->jsonb('related')->nullable()->after('chapter');

            // Best reranker score, 0 to 100: how well the top passage matches the question.
            $table->unsignedTinyInteger('confidence')->nullable()->after('related');

            // Why the evidence gate chose this state, and which generation model was configured.
            $table->string('state_reason', 300)->nullable()->after('confidence');
            $table->string('model', 100)->nullable()->after('state_reason')->index();
        });

        Schema::table('question_reviews', function (Blueprint $table) {
            // Did the cited sources actually support the answer? Null when not judged.
            $table->boolean('citation_correct')->nullable()->after('label');
            // For voice questions: what the visitor actually said, when the transcript was wrong.
            $table->text('transcript_correction')->nullable()->after('correction');
        });
    }

    public function down(): void
    {
        Schema::table('question_reviews', function (Blueprint $table) {
            $table->dropColumn(['citation_correct', 'transcript_correction']);
        });

        Schema::table('questions', function (Blueprint $table) {
            $table->dropIndex(['book']);
            $table->dropIndex(['model']);
            $table->dropColumn(['book', 'chapter', 'related', 'confidence', 'state_reason', 'model']);
        });
    }
};
