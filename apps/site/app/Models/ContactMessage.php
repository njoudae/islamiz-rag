<?php

namespace App\Models;

use App\Enums\ContactStatus;
use App\Enums\ContactTopic;
use Database\Factories\ContactMessageFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

/**
 * A message sent through the public contact page.
 */
#[Fillable(['name', 'email', 'topic', 'message', 'related_question', 'send_copy', 'visitor_id', 'ip_hash', 'user_agent'])]
class ContactMessage extends Model
{
    /** @use HasFactory<ContactMessageFactory> */
    use HasFactory;

    /**
     * @var array<string, mixed>
     */
    protected $attributes = [
        'status' => 'new',
        'send_copy' => false,
    ];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'topic' => ContactTopic::class,
            'status' => ContactStatus::class,
            'read_at' => 'datetime',
            'send_copy' => 'boolean',
        ];
    }

    /**
     * Move to a new status, stamping the first time it was read.
     */
    public function markAs(ContactStatus $status): void
    {
        $this->status = $status;
        if ($status !== ContactStatus::New) {
            $this->read_at ??= now();
        } else {
            $this->read_at = null;
        }
        $this->save();
    }
}
