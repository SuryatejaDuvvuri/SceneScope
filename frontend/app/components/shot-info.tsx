import type { ShotSuggestions } from "~/lib/types";

interface ShotInfoProps {
  shots: ShotSuggestions;
}

export function ShotInfo({ shots }: ShotInfoProps) {
  const { primary } = shots;

  return (
    <div className="p-3 bg-white/30 rounded border border-sand-600/20">
      <h4 className="text-xs font-display text-sand-700 tracking-wider mb-2">
        Suggested Shot
      </h4>
      <div className="flex flex-wrap gap-2 mb-2">
        <span className="px-2 py-0.5 text-xs font-medium bg-sand-600/15 text-sand-800 border border-sand-500/25 rounded-full">
          {primary.shot_type}
        </span>
        <span className="px-2 py-0.5 text-xs font-medium bg-sand-500/15 text-sand-700 border border-sand-400/25 rounded-full">
          {primary.angle}
        </span>
        <span className="px-2 py-0.5 text-xs font-medium bg-sand-400/15 text-sand-700 border border-sand-400/20 rounded-full">
          {primary.movement}
        </span>
      </div>
      <p className="text-xs text-stone-600 leading-relaxed">
        {primary.reasoning}
      </p>
    </div>
  );
}
