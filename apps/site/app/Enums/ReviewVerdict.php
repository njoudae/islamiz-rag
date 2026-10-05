<?php

namespace App\Enums;

enum ReviewVerdict: string
{
    case Correct = 'correct';
    case NeedsEdit = 'edit';
    case Wrong = 'wrong';

    public function label(): string
    {
        return match ($this) {
            self::Correct => 'صحيحة',
            self::NeedsEdit => 'تحتاج تعديلاً',
            self::Wrong => 'خاطئة',
        };
    }
}
