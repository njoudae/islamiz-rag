<?php

namespace App\Services\Ai;

use RuntimeException;
use Throwable;

/**
 * The AI service could not produce a usable answer.
 */
final class AiServiceException extends RuntimeException
{
    public const UNREACHABLE = 'unreachable';

    public const UPSTREAM_ERROR = 'upstream_error';

    public const INVALID_RESPONSE = 'invalid_response';

    private function __construct(
        public readonly string $reason,
        string $message,
        public readonly ?int $upstreamStatus = null,
        ?Throwable $previous = null,
    ) {
        parent::__construct($message, 0, $previous);
    }

    public static function unreachable(Throwable $previous): self
    {
        return new self(self::UNREACHABLE, 'AI service is unreachable: '.$previous->getMessage(), previous: $previous);
    }

    public static function upstreamError(int $status, string $body): self
    {
        return new self(self::UPSTREAM_ERROR, "AI service responded with HTTP {$status}: {$body}", $status);
    }

    public static function invalidResponse(string $detail): self
    {
        return new self(self::INVALID_RESPONSE, 'AI service returned an unexpected payload: '.$detail);
    }

    /**
     * Status this failure should surface as to our own API clients.
     */
    public function httpStatus(): int
    {
        return $this->reason === self::UNREACHABLE ? 503 : 502;
    }
}
