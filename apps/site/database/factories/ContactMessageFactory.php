<?php

namespace Database\Factories;

use App\Enums\ContactTopic;
use App\Models\ContactMessage;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<ContactMessage>
 */
class ContactMessageFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'name' => 'زائر تجريبي',
            'email' => fake()->safeEmail(),
            'topic' => ContactTopic::General,
            'message' => 'رسالة تجريبية من صفحة التواصل.',
        ];
    }
}
