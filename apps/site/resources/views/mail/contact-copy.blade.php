مرحباً {{ $contactMessage->name }}،

وصلت رسالتك إلى فريق دليل، وهذه نسخة منها.

الموضوع: {{ $contactMessage->topic->label() }}
@if ($contactMessage->related_question)
السؤال الذي سألته: {{ $contactMessage->related_question }}
@endif

{{ $contactMessage->message }}

سيقرأ الفريق رسالتك، وإن احتاجت رداً فسيصلك على هذا البريد.

فريق دليل
