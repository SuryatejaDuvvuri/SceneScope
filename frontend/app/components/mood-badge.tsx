import type { Mood } from "~/lib/types";

const MOOD_STYLES: Record<Mood, { bg: string; text: string; label: string }> = {
  tense: {
    bg: "bg-red-100 border border-red-300/50",
    text: "text-red-700",
    label: "Tense",
  },
  uplifting: {
    bg: "bg-amber-100 border border-amber-300/50",
    text: "text-amber-800",
    label: "Uplifting",
  },
  somber: {
    bg: "bg-slate-100 border border-slate-300/50",
    text: "text-slate-700",
    label: "Somber",
  },
  action: {
    bg: "bg-orange-100 border border-orange-300/50",
    text: "text-orange-700",
    label: "Action",
  },
};

interface MoodBadgeProps {
  mood: Mood;
  confidence?: number | null;
  size?: "sm" | "md";
}

export function MoodBadge({ mood, confidence, size = "md" }: MoodBadgeProps) {
  const style = MOOD_STYLES[mood];
  if (!style) return null;

  const sizeClasses = size === "sm" ? "text-xs px-1.5 py-0.5" : "text-sm px-2.5 py-1";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${style.bg} ${style.text} ${sizeClasses}`}
    >
      {style.label}
      {confidence != null && (
        <span className="opacity-60">{Math.round(confidence * 100)}%</span>
      )}
    </span>
  );
}
