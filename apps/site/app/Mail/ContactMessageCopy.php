<?php

namespace App\Mail;

use App\Models\ContactMessage;
use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;

/**
 * The copy a visitor asked for when sending a message from the contact page.
 */
class ContactMessageCopy extends Mailable
{
    use Queueable, SerializesModels;

    public function __construct(public ContactMessage $contactMessage) {}

    public function envelope(): Envelope
    {
        return new Envelope(subject: 'نسخة من رسالتك إلى فريق دليل');
    }

    public function content(): Content
    {
        return new Content(text: 'mail.contact-copy');
    }
}
