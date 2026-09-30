"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppShell } from "./app-shell";
import { AskComposer } from "./ask-composer";
import { CategoryGrid, FatwaList, SourceCard } from "./cards";
import { VoiceOrb } from "./voice-orb";
import { demoEntry, sourceIdentity } from "@/lib/content";
import { ArrowLeft, ArrowRight, Bookmark, Check, ChevronLeft, Copy, ExternalLink, Globe2, Headphones, Languages, Mic, Moon, Pause, Play, Search, Settings2, ShieldAlert, ShieldCheck, Sparkles, Volume2 } from "lucide-react";
import { Suspense, useEffect, useState } from "react";

type AnswerPayload = {
  state: "ANSWERABLE" | "NEEDS_CLARIFICATION" | "INSUFFICIENT_EVIDENCE" | "COMPLEX_CASE" | "CONFLICTING_EVIDENCE" | "OUT_OF_SCOPE";
  summary?: string | null;
  clarification_question?: string | null;
  escalation_message?: string | null;
  citations: Array<{ fatwa_id: number; title: string; source_url: string; excerpt?: string | null; source_collection_name?: string; source_authority?: string | null; scholar?: string | null; madhhabs?: string[]; original_reference?: Array<{ raw: string; book?: string | null; volume?: string | null; page?: string | null }>; source_type?: string }>;
};

const answerRequests = new Map<string, Promise<AnswerPayload>>();

function requestAnswer(question: string) {
  let request = answerRequests.get(question);
  if (!request) {
    request = fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: question, answer_mode: "text" }),
    }).then((response) => {
      if (!response.ok) throw new Error(`API request failed: ${response.status}`);
      return response.json() as Promise<AnswerPayload>;
    });
    answerRequests.set(question, request);
  }
  return request;
}

export function ScreenRouter({ slug }: { slug: string[] }) {
  const screen = slug[0] ?? "";
  if (screen === "onboarding") return <AppShell bare><Onboarding /></AppShell>;
  return <AppShell>{screen === "" ? <Home /> : screen === "voice" ? <Voice /> : screen === "ask" ? <TextQuestion /> : screen === "answer" ? <Suspense fallback={<PageLoader />}><Answer /></Suspense> : screen === "browse" ? <Browse /> : screen === "categories" ? <Category /> : screen === "fatwas" ? <FatwaDetail /> : screen === "search" ? <SearchScreen /> : screen === "history" ? <History /> : screen === "saved" ? <Saved /> : screen === "source" ? <SourceAbout /> : screen === "escalation" ? <Escalation /> : <Settings />}</AppShell>;
}

function Header({ title, subtitle, back = false }: { title: string; subtitle?: string; back?: boolean }) {
  return <header className="page-header">{back && <Link href="/" className="back-button"><ArrowRight size={20} /></Link>}<div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div></header>;
}

function Home() {
  return <>
    <section className="hero-panel">
      <div className="hero-panel__copy">
        <div className="hero-panel__badge"><ShieldCheck size={15} /> مصدر موثّق · إجابة مستندة إلى الأصل</div>
        <h1>اسأل بصوتك،<br />واستمع إلى الإجابة<br /><em>من مصدرها.</em></h1>
        <p>واجهة ذكية تفهم سؤالك بلغتك، وتبحث في الموسوعة الفقهية المعتمدة، ثم تعرض شرحًا موجزًا مع المادة الأصلية ومراجعها.</p>
        <div className="hero-principles"><span><ShieldCheck size={16} /> لا مصدر، لا إجابة</span><span><Languages size={16} /> عربي ومتعدد اللغات</span></div>
      </div>
      <div className="hero-panel__orb"><VoiceOrb /><small>اضغط على الكرة وابدأ الحديث</small></div>
      <AskComposer />
    </section>
    <section className="section-block">
      <div className="section-heading"><div><span>من التصنيف الرسمي</span><h2>تصفح حسب الموضوع</h2></div><Link href="/browse">عرض جميع التصنيفات <ArrowLeft size={16} /></Link></div>
      <CategoryGrid limit={6} />
    </section>
    <section className="trust-strip"><ShieldCheck size={24} /><div><strong>الإجابة مرتبطة بالمصدر</strong><span>لا نعرض حكمًا دون مادة أصلية داعمة من المجموعة المعتمدة.</span></div><Link href="/source">كيف يعمل دليل؟</Link></section>
  </>;
}

function Voice() {
  const [active, setActive] = useState(true);
  return <div className="focus-screen">
    <Header title="السؤال بالصوت" subtitle="تحدث بطبيعتك، ويمكنك التوقف في أي وقت" back />
    <div className="voice-stage">
      <div className="voice-stage__head"><div className="language-chip"><Globe2 size={16} /> العربية · اكتشاف تلقائي</div><span>تحدث بطبيعتك</span></div>
      <VoiceOrb initialState={active ? "listening" : "idle"} />
      <div className="transcript-card"><span>النص الذي فهمناه</span><p>أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟</p><i className="typing-cursor" /></div>
      <div className="voice-actions"><button className="secondary-button" onClick={() => setActive(false)}><Pause size={19} />إيقاف مؤقت</button><Link className="primary-button" href="/answer?q=أنا%20مسافر%20وسأقيم%20أربعة%20أيام،%20هل%20أقصر%20الصلاة؟"><Check size={19} />نعم، ابحث في المرجع</Link></div>
      <small className="privacy-note">واجهة الصوت تعمل حاليًا بمزوّد تجريبي قابل للاستبدال</small>
    </div>
  </div>;
}

function TextQuestion() {
  const [question, setQuestion] = useState("");
  const href = question.trim() ? `/answer?q=${encodeURIComponent(question.trim())}` : "/ask";
  return <div className="narrow-page"><Header title="اكتب سؤالك" subtitle="أضف التفاصيل التي قد تؤثر في المسألة" back /><div className="question-card"><textarea autoFocus value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="مثال: أنا مسافر وسأقيم أربعة أيام…" /><div className="question-tips"><strong>لإجابة أدق</strong><span>اذكر المدة أو التوقيت أو الظروف المهمة إن وُجدت.</span></div><Link href={href} aria-disabled={!question.trim()} className="primary-button">البحث في المرجع المعتمد <ArrowLeft size={19} /></Link></div></div>;
}

function Answer() {
  const params = useSearchParams();
  const question = params.get("q") || demoEntry.question;
  const [playing, setPlaying] = useState(false);
  const [answer, setAnswer] = useState<AnswerPayload | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setAnswer(null);
    setError(false);
    requestAnswer(question).then((payload) => { if (active) setAnswer(payload); }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [question]);

  if (error) return <div className="narrow-page"><Header title="تعذر الاتصال" back /><section className="escalation-card"><h1>تعذر الوصول إلى خدمة الإجابة</h1><p>تحقق من تشغيل الخادم المحلي ثم أعد المحاولة.</p></section></div>;
  if (!answer) return <PageLoader />;
  if (answer.state === "NEEDS_CLARIFICATION") return <div className="narrow-page"><Header title="نحتاج تفصيلًا واحدًا" back /><section className="escalation-card"><h1>{answer.clarification_question}</h1><p>هذا التفصيل ورد مؤثرًا في المصادر المسترجعة، ولن نخمن الإجابة بدونه.</p><Link href="/ask" className="primary-button">إضافة التفاصيل</Link></section></div>;
  if (answer.state !== "ANSWERABLE") return <div className="narrow-page"><Header title="التواصل مع مختص" back /><section className="escalation-card"><span className="escalation-card__icon"><ShieldAlert size={29} /></span><h1>هذه المسألة تحتاج نظرًا من مختص</h1><p>{answer.escalation_message}</p><Link href="/escalation" className="primary-button">عرض خيارات التواصل</Link></section></div>;
  const source = answer.citations[0];
  return <div className="answer-layout">
    <div className="answer-main">
      <Header title="الإجابة المبنية على المصدر" subtitle={`المرجع المعتمد: ${sourceIdentity.name}`} back />
      <section className="user-question"><span>سؤالك</span><p>{question}</p></section>
      <section className="answer-summary" aria-label="ملخص مساعد بالذكاء الاصطناعي">
        <div className="answer-summary__head"><span className="ai-mark"><Sparkles size={18} /></span><div><small>شرح موجز بالذكاء الاصطناعي</small><strong>مبني على مادة فقهية معتمدة</strong></div><span className="confidence"><ShieldCheck size={14} />أدلة كافية</span></div>
        <p>{answer.summary}</p>
        <div className="audio-player"><button onClick={() => setPlaying(!playing)} aria-label={playing ? "إيقاف" : "تشغيل"}>{playing ? <Pause size={19} /> : <Play size={19} />}</button><div><span style={{ width: playing ? "62%" : "18%" }} /><i /></div><time>٠:٤٢</time><Volume2 size={17} /></div>
        <p className="synthetic-note">المشغّل الصوتي في النسخة المحلية تجريبي، ولا يمثل صوت عالم أو جهة.</p>
      </section>
      <SourceCard source={source} />
      <div className="answer-actions"><button><Bookmark size={18} />حفظ</button><button><Copy size={18} />نسخ الملخص</button></div>
      <div className="answer-disclaimer">هذا ملخص مساعد للوصول إلى المصدر، وليس فتوى مستقلة. راجع النص الأصلي عند الحاجة.</div>
    </div>
    <aside className="answer-aside"><span>كيف وصلنا إلى الإجابة؟</span><ol><li className="done">فهم السؤال وسياقه</li><li className="done">البحث في المرجع المعتمد</li><li className="done">ترتيب المواد الأنسب</li><li className="done">التحقق من كفاية الدليل</li></ol><Link href="/escalation"><ShieldAlert size={17} />حالتي تحتاج مختصًا</Link></aside>
  </div>;
}

function Browse() {
  return <div className="wide-page"><Header title="تصفح المرجع المعتمد" subtitle="الكتب كما تظهر في فهرس الموسوعة الفقهية" /><div className="browse-toolbar"><label><Search size={19} /><input placeholder="ابحث بكلمة أو موضوع…" /></label><button><Settings2 size={18} />تصفية</button></div><CategoryGrid /><section className="section-block section-block--inner"><div className="section-heading"><div><span>من المرجع</span><h2>مواد فقهية مختارة</h2></div></div><FatwaList /></section></div>;
}

function Category() {
  return <div className="narrow-page"><Header title="الصلاة" subtitle="العبادات · من التصنيف الرسمي" back /><div className="subcategory-strip"><button className="active">الكل</button><button>أحكام الجمع</button><button>صلاة الجماعة</button><button>وقت الصلاة</button></div><FatwaList /></div>;
}

function FatwaDetail() {
  return <article className="fatwa-detail"><Header title="المادة الأصلية" back /><div className="fatwa-detail__meta"><span>كتاب الصلاة</span><span>معرّف المادة ١٤٥٥</span><span>المذاهب والمراجع محفوظة</span></div><h1>{demoEntry.title}</h1><section><h2>السياق</h2><p>{demoEntry.question}</p></section><section><h2>محتوى المصدر</h2><p>{demoEntry.originalAnswer}</p><p className="dialogue"><b>مرجع ظاهر:</b> {demoEntry.reference}</p></section><footer><ShieldCheck size={19} /><div><strong>المصدر المعتمد</strong><span>{sourceIdentity.name}</span></div><a href={demoEntry.url} target="_blank" rel="noreferrer"><ExternalLink size={17} />فتح الأصل</a></footer></article>;
}

function SearchScreen() {
  const [hasQuery, setHasQuery] = useState(false);
  return <div className="narrow-page"><Header title="البحث" subtitle="كلمات مفتاحية أو بحث دلالي بالعربية والإنجليزية" /><div className="search-hero"><label><Search size={21} /><input onChange={(e) => setHasQuery(Boolean(e.target.value))} placeholder="مثال: قصر الصلاة للمسافر" autoFocus /></label><div className="filter-pills"><button className="active">كل الكتب</button><button>كتاب الصلاة</button><button>صلاة المسافر</button></div></div>{hasQuery ? <><p className="result-count">أفضل النتائج المطابقة</p><FatwaList /></> : <div className="empty-state"><Search size={30} /><strong>ابدأ بكلمة أو سؤال</strong><p>سنبحث في عناوين المواد ومحتواها ومسارها في الفهرس المعتمد.</p></div>}</div>;
}

function History() {
  return <div className="narrow-page"><Header title="المحادثات" subtitle="أسئلتك السابقة وإجاباتها الموثقة" /><div className="conversation-list"><Link href="/answer"><span className="conversation-list__icon"><Mic size={19} /></span><div><strong>هل أقصر الصلاة إذا أقمت أربعة أيام؟</strong><small>اليوم · مادتان مستند إليهما</small></div><ChevronLeft size={18} /></Link><Link href="/answer"><span className="conversation-list__icon text"><Languages size={19} /></span><div><strong>Is intention spoken before prayer?</strong><small>أمس · إجابة باللغة الإنجليزية</small></div><ChevronLeft size={18} /></Link></div></div>;
}

function Saved() {
  return <div className="narrow-page"><Header title="المحفوظات" subtitle="المواد التي تريد الرجوع إليها" /><FatwaList savedOnly /></div>;
}

function SourceAbout() {
  return <div className="narrow-page"><Header title="المصدر وطريقة العمل" back /><section className="about-hero"><span><ShieldCheck size={27} /></span><div><small>المجموعة الافتراضية في وضع الهاكاثون</small><h1>{sourceIdentity.name}</h1><p>نحفظ بنية الكتاب والباب والفصل والمبحث، مع المذاهب والأعلام والمراجع التي تظهر صراحة.</p></div></section><div className="process-list"><div><b>١</b><span><strong>نفهم سؤالك</strong><small>نحدد اللغة والموضوع والتفاصيل المهمة.</small></span></div><div><b>٢</b><span><strong>نسترجع المادة الأصلية</strong><small>بحث هجين داخل المجموعة المعتمدة فقط.</small></span></div><div><b>٣</b><span><strong>نتحقق من كفاية الدليل</strong><small>إن لم يكن كافيًا، نسأل أو نحيلك إلى مختص.</small></span></div><div><b>٤</b><span><strong>نُظهر الهوية والمراجع</strong><small>الشرح منفصل عن المادة الأصلية وبياناتها.</small></span></div></div><a className="primary-button full" href={sourceIdentity.url} target="_blank" rel="noreferrer"><ExternalLink size={18} />زيارة الموسوعة الفقهية</a></div>;
}

function Escalation() {
  return <div className="narrow-page"><Header title="التواصل مع مختص" back /><section className="escalation-card"><span className="escalation-card__icon"><ShieldAlert size={29} /></span><h1>هذه المسألة تحتاج نظرًا من مختص</h1><p>لم نجد في المصادر المتاحة ما يكفي لإعطائك جوابًا موثقًا، أو أن تفاصيل الحالة تستدعي سؤال جهة إفتاء رسمية.</p><div className="contact-empty"><strong>لا توجد جهة اتصال موثقة مفعّلة حاليًا</strong><span>يعرض دليل فقط وسائل الاتصال التي تحقق منها مشرف النظام.</span></div><Link href="/source" className="secondary-button">تصفح المصدر الرسمي</Link></section></div>;
}

function Settings() {
  return <div className="narrow-page"><Header title="الإعدادات" subtitle="خصص تجربة السؤال والإجابة" /><div className="settings-list"><SettingRow icon={<Languages />} title="لغة الواجهة" value="العربية" /><SettingRow icon={<Headphones />} title="طريقة الإجابة" value="نص وصوت تجريبي" /><SettingRow icon={<Globe2 />} title="لغة الإجابة" value="مثل لغة السؤال" /><SettingRow icon={<Moon />} title="المظهر" value="فاتح" /><SettingRow icon={<ShieldCheck />} title="الخصوصية والمصادر" value="عرض" /></div><div className="settings-note"><strong>المجموعة الافتراضية</strong><span>{sourceIdentity.name}</span></div></div>;
}

function SettingRow({ icon, title, value }: { icon: React.ReactNode; title: string; value: string }) {
  return <button><span>{icon}</span><div><strong>{title}</strong><small>{value}</small></div><ChevronLeft size={18} /></button>;
}

function Onboarding() {
  return <div className="onboarding-card"><div className="onboarding-visual"><div className="mini-orb"><Sparkles /></div><span className="float-card f1"><ShieldCheck /> مصدر معتمد</span><span className="float-card f2"><Languages /> عربي + English</span><span className="float-card f3"><Headphones /> واجهة صوتية</span></div><div className="onboarding-copy"><span className="brand-large"><Sparkles /> دليل</span><h1>اسأل، واعرف<br />من أين جاءت الإجابة</h1><p>وصول ذكي إلى الموسوعة الفقهية المعتمدة، مع المادة الأصلية ومراجعها.</p><div className="onboarding-points"><span><Check /> لا إجابة بلا دليل</span><span><Check /> العربية أولًا</span><span><Check /> إحالة آمنة عند الحاجة</span></div><Link href="/" className="primary-button full">ابدأ الآن <ArrowLeft /></Link></div></div>;
}

function PageLoader() { return <div className="processing-state"><VoiceOrb initialState="processing" compact /><div><strong>نبحث في المرجع المعتمد</strong><span>نفهم السؤال، نسترجع المواد، ثم نتحقق من كفاية الدليل.</span></div><ol><li className="active">فهم السؤال</li><li>استرجاع المواد</li><li>التحقق من الدليل</li></ol></div>; }
