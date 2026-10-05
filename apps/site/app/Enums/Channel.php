<?php

namespace App\Enums;

/**
 * How a visitor asked. Voice questions are transcribed in the browser and
 * reach this application as text.
 */
enum Channel: string
{
    case Text = 'text';
    case Voice = 'voice';
}
