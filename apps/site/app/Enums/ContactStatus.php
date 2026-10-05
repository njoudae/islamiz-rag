<?php

namespace App\Enums;

enum ContactStatus: string
{
    case New = 'new';
    case Read = 'read';
    case Archived = 'archived';

    public function label(): string
    {
        return match ($this) {
            self::New => 'جديدة',
            self::Read => 'مقروءة',
            self::Archived => 'مؤرشفة',
        };
    }
}
