<?php

namespace App\Enums;

/**
 * Outcome of a question. The first six values mirror the AI service's
 * EvidenceState contract; Failed is recorded by this application when the
 * AI service could not be reached or returned an unusable response.
 */
enum AnswerState: string
{
    case Answerable = 'ANSWERABLE';
    case NeedsClarification = 'NEEDS_CLARIFICATION';
    case InsufficientEvidence = 'INSUFFICIENT_EVIDENCE';
    case ComplexCase = 'COMPLEX_CASE';
    case ConflictingEvidence = 'CONFLICTING_EVIDENCE';
    case OutOfScope = 'OUT_OF_SCOPE';
    case Failed = 'FAILED';

    public function label(): string
    {
        return match ($this) {
            self::Answerable => 'تمت الإجابة',
            self::NeedsClarification => 'يحتاج توضيحًا',
            self::InsufficientEvidence => 'دليل غير كافٍ',
            self::ComplexCase => 'حالة معقدة',
            self::ConflictingEvidence => 'أدلة متعارضة',
            self::OutOfScope => 'خارج النطاق',
            self::Failed => 'تعذّرت المعالجة',
        };
    }

    /**
     * Coarse grouping used by the admin dashboard.
     */
    public function outcome(): string
    {
        return match ($this) {
            self::Answerable => 'answered',
            self::NeedsClarification => 'clarification',
            self::Failed => 'failed',
            default => 'unanswered',
        };
    }

    /**
     * States in which the visitor left without an answer or a follow-up question.
     *
     * @return list<self>
     */
    public static function unanswered(): array
    {
        return [
            self::InsufficientEvidence,
            self::ComplexCase,
            self::ConflictingEvidence,
            self::OutOfScope,
            self::Failed,
        ];
    }
}
