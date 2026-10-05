<?php

namespace App\Support;

/**
 * Small Arabic text helpers shared by analytics.
 */
final class Arabic
{
    /**
     * Remove short vowels and tatweel, so "كِتابُ الصَّلاةِ" and "كتاب الصلاة" compare equal.
     */
    public static function stripDiacritics(string $text): string
    {
        return trim((string) preg_replace('/[\x{064B}-\x{0652}\x{0670}\x{0640}]/u', '', $text));
    }

    /**
     * Loose form for grouping the same question typed slightly differently.
     */
    public static function normalize(string $text): string
    {
        $text = self::stripDiacritics($text);
        $text = strtr($text, ['أ' => 'ا', 'إ' => 'ا', 'آ' => 'ا', 'ٱ' => 'ا', 'ى' => 'ي', 'ة' => 'ه']);
        $text = (string) preg_replace('/[^\p{L}\p{N}\s]+/u', ' ', $text);

        return mb_strtolower(trim((string) preg_replace('/\s+/u', ' ', $text)));
    }

    /**
     * @return list<string>
     */
    public static function words(string $text): array
    {
        $normalized = self::normalize($text);

        return $normalized === '' ? [] : explode(' ', $normalized);
    }
}
