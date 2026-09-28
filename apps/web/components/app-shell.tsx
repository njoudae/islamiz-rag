"use client";

import Link from "next/link";
import { Bookmark, Globe2, House, MessageCircleMore, Search, Settings, Sparkles } from "lucide-react";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "الرئيسية", icon: House },
  { href: "/browse", label: "التصفح", icon: Search },
  { href: "/history", label: "المحادثات", icon: MessageCircleMore },
  { href: "/saved", label: "المحفوظات", icon: Bookmark },
];

export function AppShell({ children, bare = false }: { children: React.ReactNode; bare?: boolean }) {
  const path = usePathname();
  if (bare) return <main className="onboarding-shell">{children}</main>;
  return (
    <div className="app-frame">
      <header className="topbar">
        <Link href="/" className="brand" aria-label="دليل - الرئيسية"><span className="brand__mark"><Sparkles size={18} /></span><span><b>دليل</b><small>وصول موثّق إلى المرجع المعتمد</small></span></Link>
        <nav className="desktop-nav" aria-label="التنقل الرئيسي">
          {nav.map(({ href, label }) => <Link key={href} href={href} className={path === href ? "active" : ""}>{label}</Link>)}
        </nav>
        <div className="topbar__actions">
          <button className="language-button" type="button" aria-label="تغيير اللغة"><Globe2 size={18} /><span>العربية</span></button>
          <Link href="/settings" className="icon-button" aria-label="الإعدادات"><Settings size={19} /></Link>
        </div>
      </header>
      <main className="main-content">{children}</main>
      <nav className="bottom-nav" aria-label="التنقل الرئيسي">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href;
          return <Link key={href} href={href} className={active ? "active" : ""}><Icon size={21} /><span>{label}</span></Link>;
        })}
      </nav>
    </div>
  );
}
