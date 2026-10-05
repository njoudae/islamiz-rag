<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\Http;

abstract class TestCase extends BaseTestCase
{
    /** What the AI service reports about itself in tests. */
    public const AI_INFO = [
        'models' => ['generation' => 'test-model', 'embedding' => 'test-embedder', 'reranker' => 'test-reranker'],
        'index' => [
            'documents' => 40,
            'chunks' => 88,
            'indexed_at' => '2026-10-02T16:46:34+00:00',
            'books' => [['title' => 'كِتابُ الصَّلاةِ', 'entries' => 40]],
            'chapters' => [['book' => 'كِتابُ الصَّلاةِ', 'title' => 'الفَصْلُ الأَوَّل: صلاةُ المُسافِر', 'entries' => 16]],
        ],
    ];

    protected function setUp(): void
    {
        parent::setUp();

        // Pages are asserted through Inertia props; tests must not depend on a built frontend.
        $this->withoutVite();

        // Every page shares the AI service's index summary; tests never reach a real service for it.
        Http::fake(['*/v1/info' => Http::response(self::AI_INFO)]);
    }
}
