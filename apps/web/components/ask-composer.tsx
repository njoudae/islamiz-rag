"use client";

import { ArrowLeft, ChevronDown, Mic } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function AskComposer() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim()) router.push(`/answer?q=${encodeURIComponent(question.trim())}`);
  }
  return (
    <form className="composer" onSubmit={submit}>
      <div className="composer__field">
        <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="اكتب سؤالك كما تقوله…" aria-label="سؤالك" />
        <button type="submit" className="composer__send" aria-label="البحث عن الإجابة"><span>ابحث</span><ArrowLeft size={19} /></button>
      </div>
      <div className="composer__options">
        <button type="button"><small>لغة السؤال</small><span>العربية <ChevronDown size={14} /></span></button>
        <button type="button"><small>طريقة الإجابة</small><span>نص وصوت <ChevronDown size={14} /></span></button>
        <LinkMic />
      </div>
    </form>
  );
}

function LinkMic() {
  const router = useRouter();
  return <button type="button" className="composer__mic" onClick={() => router.push("/voice")} aria-label="اسأل بالصوت"><Mic size={19} /><span>اسأل بصوتك</span></button>;
}
