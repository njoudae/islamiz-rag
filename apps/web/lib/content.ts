import { BookOpenText, Droplets, HandCoins, Landmark, MoonStar, Plane, Salad, Shirt } from "lucide-react";

export const sourceIdentity = {
  collection: "OFFICIAL_HACKATHON_REFERENCE",
  name: "الموسوعة الفقهية – الدرر السنية",
  authority: "مؤسسة الدرر السنية",
  domain: "dorar.net/feqhia",
  url: "https://dorar.net/feqhia",
  methodologyUrl: "https://dorar.net/article/1923",
};

// Exact top-level books visible in the approved reference index.
export const categories = [
  { slug: "tahara", name: "كتاب الطهارة", count: "من الفهرس المعتمد", icon: Droplets, tone: "sky" },
  { slug: "salah", name: "كتاب الصلاة", count: "من الفهرس المعتمد", icon: Landmark, tone: "mint" },
  { slug: "zakat", name: "كتاب الزكاة", count: "من الفهرس المعتمد", icon: HandCoins, tone: "lime" },
  { slug: "siyam", name: "كتاب الصوم", count: "من الفهرس المعتمد", icon: MoonStar, tone: "peach" },
  { slug: "hajj", name: "كتاب الحج", count: "من الفهرس المعتمد", icon: Plane, tone: "violet" },
  { slug: "clothing", name: "كتاب اللباس والزينة", count: "من الفهرس المعتمد", icon: Shirt, tone: "rose" },
  { slug: "drinks", name: "كتاب الأشربة", count: "من الفهرس المعتمد", icon: BookOpenText, tone: "amber" },
  { slug: "food", name: "كتاب الأطعمة", count: "من الفهرس المعتمد", icon: Salad, tone: "blue" },
] as const;

export const demoEntry = {
  id: "1455",
  title: "عدم نية الإقامة في السفر",
  question: "أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟",
  summary: "تعرض المادة المعتمدة حكم من نوى الإقامة، وتعرض الأقوال الرئيسة في المدة التي تقطع حكم السفر مع أدلة كل قول وعزوه. لا يختار المساعد قولًا من عنده، ويُبقي تفاصيل المرجع ظاهرة.",
  excerpt: "اختلف العلماء في مدة الإقامة التي تقطع حكم السفر، وتعرض المادة الأقوال وأدلتها وعزوها.",
  originalAnswer: "المادة الفقهية تعرض حكم من نوى الإقامة، ثم تفصل الأقوال في المدة التي تقطع حكم السفر، وتربط كل قول بالمذاهب والأدلة والمراجع الأصلية.",
  url: "https://dorar.net/feqhia/1455/%D8%A7%D9%84%D9%85%D8%B7%D9%84%D8%A8-%D8%A7%D9%84%D8%AB%D8%A7%D9%86%D9%8A-%D8%B9%D8%AF%D9%85-%D9%86%D9%8A%D8%A9-%D8%A7%D9%84%D8%A5%D9%82%D8%A7%D9%85%D8%A9-%D9%81%D9%8A-%D8%A7%D9%84%D8%B3%D9%81%D8%B1",
  authority: sourceIdentity.authority,
  collectionName: sourceIdentity.name,
  madhhabs: ["المالكية", "الشافعية", "الحنابلة"],
  reference: "الاستذكار 2/242",
};

export const recent = [
  { title: "عدم نية الإقامة في السفر", category: "صلاة المسافر", id: "1455", saved: true },
  { title: "أن يكون السفر مسافة قصر", category: "شروط قصر الصلاة", id: "1453", saved: true },
  { title: "تعريف قصر الصلاة", category: "صلاة المسافر", id: "1444", saved: false },
  { title: "مشروعية القصر في السفر", category: "صلاة المسافر", id: "1446", saved: false },
];
