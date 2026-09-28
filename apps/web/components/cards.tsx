import Link from "next/link";
import { ArrowLeft, Bookmark, ExternalLink, ShieldCheck } from "lucide-react";
import { categories, demoEntry, recent, sourceIdentity } from "@/lib/content";

export function CategoryGrid({ limit }: { limit?: number }) {
  const items = limit ? categories.slice(0, limit) : categories;
  return <div className="category-grid">{items.map(({ slug, name, count, icon: Icon, tone }) => (
    <Link href={`/categories/${slug}`} className={`category-card tone-${tone}`} key={slug}>
      <span className="category-card__icon"><Icon size={24} /></span><strong>{name}</strong><small>{count}</small><ArrowLeft className="category-card__arrow" size={17} />
    </Link>
  ))}</div>;
}

export function FatwaList({ savedOnly = false }: { savedOnly?: boolean }) {
  const items = savedOnly ? recent.filter((item) => item.saved) : recent;
  return <div className="fatwa-list">{items.map((item) => (
    <Link href={`/fatwas/${item.id}`} className="fatwa-row" key={item.id}>
      <span className="fatwa-row__icon"><Bookmark size={18} fill={item.saved ? "currentColor" : "none"} /></span>
      <span><small>{item.category}</small><strong>{item.title}</strong><em>{sourceIdentity.name}</em></span><ArrowLeft size={18} />
    </Link>
  ))}</div>;
}

type SourceView = {
  title: string;
  excerpt?: string | null;
  source_url: string;
  source_collection_name?: string;
  source_authority?: string | null;
  scholar?: string | null;
  madhhabs?: string[];
  original_reference?: Array<{ raw: string; book?: string | null; volume?: string | null; page?: string | null }>;
  source_type?: string;
};

export function SourceCard({ compact = false, source }: { compact?: boolean; source?: SourceView }) {
  const title = source?.title ?? demoEntry.title;
  const excerpt = source?.excerpt ?? demoEntry.excerpt;
  const url = source?.source_url ?? demoEntry.url;
  const collectionName = source?.source_collection_name ?? demoEntry.collectionName;
  const authority = source?.source_authority ?? demoEntry.authority;
  const madhhabs = source?.madhhabs ?? demoEntry.madhhabs;
  const reference = source?.original_reference?.[0]?.raw ?? demoEntry.reference;
  return <section className={`source-card ${compact ? "source-card--compact" : ""}`}>
    <div className="source-card__eyebrow"><ShieldCheck size={17} /><span>المصدر الأصلي</span><b>موثّق</b></div>
    <p className="source-card__author">{collectionName}</p>
    <h3>{title}</h3>
    {!compact && excerpt && <><span className="source-card__label">النص المستند إليه</span><blockquote>«{excerpt}»</blockquote></>}
    {!compact && <dl className="source-card__metadata"><div><dt>الجهة</dt><dd>{authority}</dd></div>{madhhabs.length > 0 && <div><dt>المذاهب المذكورة</dt><dd>{madhhabs.join("، ")}</dd></div>}{reference && <div><dt>مرجع ظاهر</dt><dd>{reference}</dd></div>}</dl>}
    <div className="source-card__actions"><a href={url} target="_blank" rel="noreferrer"><ExternalLink size={17} />فتح المادة الأصلية</a></div>
  </section>;
}
