<?php

namespace App\Http\Requests\Admin;

use Carbon\CarbonImmutable;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/**
 * The 7, 30 or 90-day window the dashboard pages are viewed through.
 */
class PeriodRequest extends FormRequest
{
    public const PERIODS = [7, 30, 90];

    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, mixed>
     */
    public function rules(): array
    {
        return ['period' => ['nullable', 'integer', Rule::in(self::PERIODS)]];
    }

    public function period(): int
    {
        return (int) ($this->validated('period') ?? 30);
    }

    /**
     * First day of the current window; the previous window ends the day before.
     */
    public function windowStart(): CarbonImmutable
    {
        return CarbonImmutable::today()->subDays($this->period() - 1);
    }
}
