import type { Metadata } from "next";
import "./globals.css";
import "./source-metadata.css";

export const metadata: Metadata = {
  title: "دليل | إجابات موثقة من المصدر",
  description: "واجهة ذكية متعددة اللغات للوصول إلى المعرفة الشرعية من المرجع المعتمد، مع إظهار المادة الأصلية ومراجعها.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
