import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  GitBranch,
  TerminalSquare,
} from "lucide-react";

export const PRODUCT = {
  name: "Interactive Curriculum Engine",
  shortName: "ICE",
  tagline: "Escape Tutorial Hell.",
  subTagline:
    "Convert Passive Educational Coding Videos into Interactive, Personalized Learning Sessions.",
  problem:
    "Developers spend thousands of hours watching tutorials line-by-line but fail to write code independently because passive watching doesn't build independent reasoning.",
  features: [
    {
      key: "ingestion",
      label: "Video Ingestion",
      detail: "Submit any YouTube URL or upload MP4 tutorials.",
    },
    {
      key: "segmentation",
      label: "Concept Segmentation & AI Checkpoints",
      detail: "The engine auto-pauses videos at optimal concept shifts.",
    },
    {
      key: "overlays",
      label: "Dynamic Practice Overlays",
      detail:
        "Coding Challenges in a new problem space, Debugging Snippets, MCQs, and Free-Text Conceptual Questions.",
    },
    {
      key: "sandbox",
      label: "Sandboxed Code Execution",
      detail:
        "Integrated Python compiler with automatic test-case verification and immediate visual feedback.",
    },
    {
      key: "adaptive",
      label: "Adaptive Progression",
      detail:
        "IRT-driven difficulty scaling; inserts remedial variants on failure.",
    },
    {
      key: "analytics",
      label: "Learner Analytics Dashboard",
      detail:
        "Concept mastery metrics, accuracy streaks, and your Tutorial Hell Score.",
    },
  ],
} as const;

export type ProductFeature = (typeof PRODUCT.features)[number];

export interface NavLink {
  label: string;
  href: string;
}

export const NAV_LINKS: NavLink[] = [
  { label: "Get Started", href: "/upload" },
  { label: "Features", href: "#features" },
  { label: "Pricing", href: "#pricing" },

  { label: "Solutions", href: "#solutions" },
  { label: "Enterprise", href: "#enterprise" },
];

export const HERO_COPY = {
  typewriter: [
    "A place to escape tutorial hell.",
    "Ingest, Segment, & Master coding tutorials in real-time.",
  ],
  primaryCta: "Break the Cycle for $12.99/mo",
  secondaryCta: "See How it Works",
  floatingTags: ["@Zubair", "@Aryan", "@Ahmed"] as const,
  cardColors: ["lime", "coral", "hotpink", "blue", "orange"] as const,
};

export interface MarqueeLogo {
  name: string;
  label: string;
}

export const MARQUEE_LOGOS: MarqueeLogo[] = [
  { name: "judge0", label: "Judge0" },
  { name: "fastapi", label: "FastAPI" },
  { name: "nextjs", label: "Next.js" },
  { name: "celery", label: "Celery" },
  { name: "redis", label: "Redis" },
  { name: "pytorch", label: "PyTorch" },
  { name: "postgresql", label: "PostgreSQL" },
  { name: "docker", label: "Docker" },
];

export interface ExerciseType {
  key: string;
  title: string;
  description: string;
  bgClass: string;
  rotate: number;
  yOffset: number;
  image: string;
}

export const EXERCISE_TYPES: ExerciseType[] = [
  {
    key: "mcq",
    title: "MCQ Checkpoints",
    description: "Conceptual multiple-choice gates at every segment boundary.",
    bgClass: "bg-blue",
    rotate: -8,
    yOffset: 0,
    image: "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?q=80&w=600&auto=format&fit=crop",
  },
  {
    key: "coding",
    title: "Coding Labs",
    description: "Sandboxed Python challenges in a new problem space.",
    bgClass: "bg-orange",
    rotate: 0,
    yOffset: -12,
    image: "https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=600&auto=format&fit=crop",
  },
  {
    key: "debugging",
    title: "Debugging Snippets",
    description: "Fix broken code pulled directly from tutorial context.",
    bgClass: "bg-purple",
    rotate: 8,
    yOffset: 0,
    image: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=600&auto=format&fit=crop",
  },
];

export interface VisionIcon {
  Icon: LucideIcon;
  label: string;
  rotate: number;
  x: number;
  y: number;
  delay: string;
}

export const VISION_ICONS: VisionIcon[] = [
  { Icon: Cpu, label: "Video ingestion pipeline", rotate: -6, x: 0, y: 0, delay: "0s" },
  { Icon: BrainCircuit, label: "AI checkpoint engine", rotate: 4, x: 72, y: -20, delay: "0.4s" },
  { Icon: GitBranch, label: "Concept segmentation", rotate: -3, x: 140, y: 24, delay: "0.8s" },
  { Icon: TerminalSquare, label: "Sandboxed execution", rotate: 8, x: 40, y: 64, delay: "1.2s" },
  { Icon: BarChart3, label: "Mastery analytics", rotate: -5, x: 120, y: 80, delay: "1.6s" },
  { Icon: CheckCircle2, label: "Adaptive progression", rotate: 6, x: 200, y: 40, delay: "2s" },
];

export interface FeatureCard {
  key: string;
  title: string;
  description: string;
  variant: "light" | "blue" | "photo" | "dark";
  badge?: string;
  telemetry?: string[];
}

export const FEATURE_CARDS: FeatureCard[] = [
  {
    key: "ingest",
    title: "Connect, Ingest, Compile",
    description:
      "Pipe YouTube URLs or MP4 uploads into ICE's ingestion worker and watch checkpoints compile in real-time.",
    variant: "light",
    badge: "@ingestion-worker",
  },
  {
    key: "automation",
    title: "Where Logic Meets Automation",
    description:
      "AI segmentation maps concept shifts and inserts practice overlays at the exact moment transfer breaks down.",
    variant: "blue",
  },
  {
    key: "concepts",
    title: "Spin Complex Concepts into Code",
    description:
      "Every checkpoint spins abstract tutorial narration into executable Python with live accuracy telemetry.",
    variant: "photo",
    telemetry: ["Concept: Recursion", "Accuracy: 84%"],
  },
];

export interface CurriculumItem {
  id: string;
  title: string;
  lessons: number;
  progress: number;
  accent: string;
}

export const CURRICULUM_ITEMS: CurriculumItem[] = [
  {
    id: "fastapi",
    title: "FastAPI Architecture",
    lessons: 24,
    progress: 72,
    accent: "bg-blue",
  },
  {
    id: "pandas",
    title: "Pandas Data Mastery",
    lessons: 18,
    progress: 45,
    accent: "bg-orange",
  },
  {
    id: "react",
    title: "Advanced React States",
    lessons: 21,
    progress: 88,
    accent: "bg-hotpink",
  },
  {
    id: "sandbox",
    title: "Sandbox Execution Internals",
    lessons: 14,
    progress: 33,
    accent: "bg-purple",
  },
  {
    id: "irt",
    title: "IRT Adaptive Scaling Explained",
    lessons: 12,
    progress: 61,
    accent: "bg-lime",
  },
];

export interface PricingTier {
  id: string;
  name: string;
  price: string;
  period: string;
  highlight?: boolean;
  badge?: string;
  ribbon?: string;
  features: string[];
  className: string;
  rotate: string;
}

export const PRICING_TIERS: PricingTier[] = [
  {
    id: "monthly",
    name: "Monthly",
    price: "$9.99",
    period: "/mo",
    features: [
      "500 sandbox executions per month",
      "50 AI checkpoint generations",
      "Learner analytics dashboard",
      "YouTube & MP4 ingestion",
      "MCQ + coding overlay access",
    ],
    className: "bg-white border border-ink/10",
    rotate: "sm:rotate-[-3deg] sm:translate-y-2",
  },
  {
    id: "quarterly",
    name: "Quarterly",
    price: "$12.99",
    period: "/mo",
    highlight: true,
    badge: "Popular",
    features: [
      "2,000 sandbox executions per month",
      "Unlimited AI checkpoint generations",
      "IRT adaptive progression engine",
      "Tutorial Hell Score tracking",
      "Priority ingestion queue",
    ],
    className: "bg-orange text-white",
    rotate: "sm:rotate-0 sm:scale-105 sm:z-10",
  },
  {
    id: "annually",
    name: "Annually",
    price: "$19.99",
    period: "/mo",
    ribbon: "Save 10%",
    features: [
      "Unlimited sandbox executions",
      "Enterprise cohort dashboard",
      "Bulk curriculum ingestion",
      "Remedial variant auto-insertion",
      "Dedicated analytics export",
    ],
    className: "bg-white border border-ink/10",
    rotate: "sm:rotate-[3deg] sm:translate-y-2",
  },
];

export interface FooterColumn {
  title?: string;
  links: { label: string; href: string }[];
}

export const FOOTER_COLUMNS: FooterColumn[] = [
  {
    links: [
      { label: "Get Started", href: "/upload" },
      { label: "Pricing", href: "#pricing" },
      { label: "Contact", href: "#contact" },
      { label: "Solution", href: "#solutions" },
    ],
  },
  {
    links: [
      { label: "Your Story", href: "#about" },
      { label: "Create Curriculum", href: "/upload" },
      { label: "Sell Assets", href: "#marketplace" },
    ],
  },
  {
    links: [
      { label: "Privacy", href: "#privacy" },
      { label: "Policy", href: "#policy" },
      { label: "Terms", href: "#terms" },
    ],
  },
  {
    links: [{ label: "API Documentation", href: "#api" }],
  },
];

export const TOOL_BELT_ICONS = [
  "Docker",
  "PostgreSQL",
  "Redis",
  "Celery",
  "FastAPI",
  "pgvector",
] as const;

export interface LearnerChip {
  id: string;
  type: "avatar" | "stat";
  label: string;
  x: number;
  y: number;
  size: number;
}

function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

export function generateLearnerChips(count: number): LearnerChip[] {
  const stats = [
    "92% mastery",
    "78% accuracy",
    "14-day streak",
    "IRT: Advanced",
    "Hell Score: 12",
    "6 concepts solid",
  ];
  const names = ["Trisha", "Zubair", "Aryan", "Ahmed", "Priya", "Marcus", "Sara", "Devon"];

  return Array.from({ length: count }, (_, i) => {
    const isAvatar = i % 3 !== 0;
    return {
      id: `chip-${i}`,
      type: isAvatar ? "avatar" : "stat",
      label: isAvatar
        ? names[i % names.length]
        : stats[i % stats.length],
      x: 5 + seededRandom(i * 7) * 85,
      y: 5 + seededRandom(i * 13 + 3) * 80,
      size: isAvatar ? 40 + Math.floor(seededRandom(i * 5) * 16) : 0,
    };
  });
}

export const LEARNER_CHIPS_DESKTOP = generateLearnerChips(16);
export const LEARNER_CHIPS_MOBILE = generateLearnerChips(8);

export const NEON_MARQUEE_TEXT =
  "INSPIRED BY COGNITIVE TRANSFER • DISRUPT PASSIVE VIEWING • BUILD THE ENGINE • ";

export const INSTRUCTOR_SPOTLIGHT = {
  label: "CLASS BY AI EXPERTS",
  headline: "Gateway to engineering mastery.",
  tabs: ["Overview", "Curriculum Map"] as const,
  cta: "Watch Demo",
};

export const VALUE_PROPOSITION_COPY =
  "Whether you're an aspiring developer looking to build projects independently, or an instructor seeking to scale interactive coursework, ICE connects raw video to instant practice.";

export const VISION_COPY = {
  heading: "Our vision for active learning architecture.",
  body: `${PRODUCT.problem} ICE replaces passive replay with checkpoint-driven practice — forcing you to write, debug, and explain code at the exact moments concepts shift, so transfer-of-understanding replaces tutorial amnesia.`,
};

export const LEARNER_MATRIX_COPY = {
  headline: "You will find yourself among the best.",
  subcaption:
    "Dive into a dynamic ecosystem where learning tracks and visual validation merge.",
};

export const MARKETPLACE_COPY = {
  badge: "GET MORE CLOSER",
  headline: "Marketplace for Interactive Curricula.",
  body: "Browse AI-generated learning paths compiled from real tutorial footage — each curriculum ships with checkpoints, sandbox labs, and mastery telemetry baked in.",
  cta: "View All",
};

export const PRICING_COPY = {
  heading: "Flexible tiered membership for every learner.",
  body: "Scale from solo tutorial escape to enterprise cohort deployment. Every tier includes sandbox execution, checkpoint generation, and dashboard access.",
  bullets: [
    "Sandboxed Python executions per month",
    "AI checkpoint & overlay generation",
    "Learner analytics dashboard access",
    "YouTube URL + MP4 ingestion pipeline",
  ],
};

export const DUAL_CTA = [
  {
    key: "peers",
    title: "Meets your peer group.",
    subtitle: "Connect with builders to code and review works.",
    cta: "Let's Meet",
    bgClass: "bg-surfaceBurgundy",
    buttonClass: "bg-white text-surfaceBurgundy",
  },
  {
    key: "archive",
    title: "Archive your mastery.",
    subtitle: "Build an immune system against forgotten tutorial syntax.",
    cta: "Archive Portfolio",
    bgClass: "bg-surfaceDark",
    buttonClass: "bg-lime text-ink",
  },
] as const;

export const COMPONENT_GRID_PROFILE = {
  name: "Trisha Woodward",
  caption: "via AI-Pipeline",
  codeSnippet: `def checkpoint_passed(score: float) -> bool:\n    return score >= 0.84 and mastery_node.solidified`,
};

export const SOCIAL_LINKS = [
  { label: "GitHub", href: "https://github.com" },
  { label: "Twitter", href: "https://twitter.com" },
  { label: "LinkedIn", href: "https://linkedin.com" },
  { label: "YouTube", href: "https://youtube.com" },
] as const;
