import { notFound } from "next/navigation";
import { ScreenRouter } from "@/components/screens";

export default async function CatchAllPage({ params }: { params: Promise<{ slug?: string[] }> }) {
  const { slug = [] } = await params;
  const known = ["", "onboarding", "voice", "ask", "answer", "browse", "categories", "fatwas", "search", "history", "saved", "source", "escalation", "settings"];
  if (!known.includes(slug[0] ?? "")) notFound();
  return <ScreenRouter slug={slug} />;
}

