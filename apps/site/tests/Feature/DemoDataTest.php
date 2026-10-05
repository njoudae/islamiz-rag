<?php

namespace Tests\Feature;

use App\Models\Question;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class DemoDataTest extends TestCase
{
    use RefreshDatabase;

    public function test_demo_rows_are_flagged_and_can_be_purged_without_touching_real_ones(): void
    {
        $real = Question::factory()->create();

        $this->artisan('daleel:demo-data', ['--days' => 3, '--per-day' => 5])->assertSuccessful();

        $this->assertGreaterThan(0, Question::where('is_demo', true)->count());
        $this->assertFalse($real->refresh()->is_demo);

        $this->artisan('daleel:demo-data', ['--purge' => true])->assertSuccessful();

        $this->assertSame(0, Question::where('is_demo', true)->count());
        $this->assertTrue(Question::whereKey($real->id)->exists());
    }
}
