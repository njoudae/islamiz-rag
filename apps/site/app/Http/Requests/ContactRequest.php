<?php

namespace App\Http\Requests;

use App\Enums\ContactTopic;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class ContactRequest extends FormRequest
{
    public const MESSAGE_MAX = 1500;

    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, mixed>
     */
    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:100'],
            'email' => ['required', 'string', 'email', 'max:190'],
            'topic' => ['required', Rule::enum(ContactTopic::class)],
            'related_question' => ['nullable', 'string', 'max:1000'],
            'message' => ['required', 'string', 'min:10', 'max:'.self::MESSAGE_MAX],
            'send_copy' => ['boolean'],
            'visitor_id' => ['nullable', 'uuid'],
            // Honeypot: hidden from people, often filled in by bots.
            'website' => ['nullable', 'string', 'max:200'],
        ];
    }

    /**
     * @return array<string, string>
     */
    public function messages(): array
    {
        return [
            'name.required' => 'اكتب اسمك.',
            'name.max' => 'الاسم طويل جداً.',
            'email.required' => 'اكتب بريدك الإلكتروني لنتمكن من الرد.',
            'email.email' => 'صيغة البريد غير صحيحة، مثل name@example.com.',
            'topic.required' => 'اختر موضوع الرسالة.',
            'topic.enum' => 'اختر موضوعاً من القائمة.',
            'related_question.max' => 'نص السؤال طويل جداً. الصق السؤال وحده.',
            'message.required' => 'اكتب رسالتك.',
            'message.min' => 'الرسالة قصيرة جداً. اكتب عشرة أحرف على الأقل.',
            'message.max' => 'الرسالة طويلة جداً. اختصرها إلى '.self::MESSAGE_MAX.' حرف.',
        ];
    }

    public function isSpam(): bool
    {
        return filled($this->input('website'));
    }
}
