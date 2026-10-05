<?php

namespace App\Http\Controllers\Api\V1;

use App\Actions\AskQuestion;
use App\Enums\AnswerState;
use App\Enums\Channel;
use App\Http\Controllers\Controller;
use App\Http\Requests\AskRequest;
use App\Http\Resources\AnswerResource;
use App\Models\Question;
use App\Services\Ai\AiServiceException;
use Illuminate\Http\JsonResponse;

class AskController extends Controller
{
    public function __invoke(AskRequest $request, AskQuestion $ask): JsonResponse
    {
        $parentId = $request->validated('parent_id');

        $question = $ask->handle(
            query: $request->validated('query'),
            language: $request->validated('language'),
            answerMode: $request->validated('answer_mode') ?? 'text',
            channel: Channel::tryFrom((string) $request->validated('channel')) ?? Channel::Text,
            parent: $parentId ? Question::find($parentId) : null,
            visitor: [
                'visitor_id' => $request->validated('visitor_id'),
                'ip' => $request->ip(),
                'user_agent' => $request->userAgent(),
            ],
        );

        if ($question->state === AnswerState::Failed) {
            return response()->json([
                'message' => 'تعذّر الوصول إلى خدمة الإجابة حاليًا. حاول مرة أخرى بعد قليل.',
                'state' => AnswerState::Failed->value,
                'error' => $question->error_code,
                'id' => $question->id,
            ], $question->error_code === AiServiceException::UNREACHABLE ? 503 : 502);
        }

        // 200 rather than the resource default of 201: callers ask a question, they do not create a record.
        return AnswerResource::make($question)->response()->setStatusCode(200);
    }
}
