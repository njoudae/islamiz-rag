"use client";

import { Mic, Volume2, LoaderCircle, AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";

export type OrbState = "idle" | "listening" | "processing" | "speaking" | "error";

const labels: Record<OrbState, string> = {
  idle: "اضغط للتحدث",
  listening: "أستمع إليك…",
  processing: "أبحث في المرجع…",
  speaking: "أقرأ الإجابة…",
  error: "تعذر التقاط الصوت",
};

export function VoiceOrb({ initialState = "idle", compact = false }: { initialState?: OrbState; compact?: boolean }) {
  const [state, setState] = useState<OrbState>(initialState);

  useEffect(() => setState(initialState), [initialState]);

  function cycle() {
    if (state === "idle" || state === "error") setState("listening");
    else if (state === "listening") setState("processing");
    else if (state === "processing") setState("speaking");
    else setState("idle");
  }

  const Icon = state === "processing" ? LoaderCircle : state === "speaking" ? Volume2 : state === "error" ? AlertTriangle : Mic;
  return (
    <button className={`orb orb--${state} ${compact ? "orb--compact" : ""}`} onClick={cycle} aria-label={labels[state]} type="button">
      <span className="orb__halo" aria-hidden="true" />
      <span className="orb__orbit orb__orbit--one" aria-hidden="true" />
      <span className="orb__orbit orb__orbit--two" aria-hidden="true" />
      <span className="orb__mesh" aria-hidden="true"><i /><i /><i /><i /><i /></span>
      <span className="orb__core"><Icon size={compact ? 24 : 30} strokeWidth={1.8} /></span>
      {!compact && <span className="orb__label">{labels[state]}</span>}
    </button>
  );
}
