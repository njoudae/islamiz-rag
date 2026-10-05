<?php

namespace App\Http\Requests;

use App\Enums\Channel;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class AskRequest extends FormRequest
{
    public function authorize(): bool
    {
        // Visitors use the tool without an account.
        return true;
    }

    /**
     * The anonymous visitor id travels in a header so the request body stays
     * close to the AI service's own contract.
     */
    protected function prepareForValidation(): void
    {
        if ($this->hasHeader('X-Visitor-Id')) {
            $this->merge(['visitor_id' => $this->header('X-Visitor-Id')]);
        }
    }

    /**
     * @return array<string, mixed>
     */
    public function rules(): array
    {
        return [
            'query' => ['required', 'string', 'min:3', 'max:4000'],
            'language' => ['nullable', 'string', 'max:16'],
            'answer_mode' => ['nullable', Rule::in(['text', 'voice', 'both'])],
            'channel' => ['nullable', Rule::enum(Channel::class)],
            'parent_id' => ['nullable', 'integer', Rule::exists('questions', 'id')],
            'visitor_id' => ['nullable', 'uuid'],
        ];
    }
}
