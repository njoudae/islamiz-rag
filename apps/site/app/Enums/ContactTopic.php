<?php

namespace App\Enums;

/**
 * Topics offered on the contact page, in the order they are listed.
 * The first one is preselected.
 */
enum ContactTopic: string
{
    case AnswerFeedback = 'answer_feedback';
    case SourceSuggestion = 'source_suggestion';
    case Suggestion = 'suggestion';
    case Technical = 'technical';
    case General = 'general';
    case Other = 'other';

    public function label(): string
    {
        return match ($this) {
            self::AnswerFeedback => 'الإبلاغ عن خطأ في إجابة',
            self::SourceSuggestion => 'اقتراح مصدر علمي',
            self::Suggestion => 'اقتراح تحسين',
            self::Technical => 'مشكلة تقنية',
            self::General => 'استفسار عام',
            self::Other => 'أخرى',
        };
    }

    /**
     * @return list<array{value: string, label: string}>
     */
    public static function options(): array
    {
        return array_map(fn (self $t) => ['value' => $t->value, 'label' => $t->label()], self::cases());
    }
}
