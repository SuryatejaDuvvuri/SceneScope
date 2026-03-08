import type { ShotSuggestions } from "~/lib/types";

interface ShotInfoProps {
  shots: ShotSuggestions;
}

export function ShotInfo({ shots }: ShotInfoProps) {
  const { primary } = shots;

  return (
    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
      <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
        Suggested Shot
      </h4>
      <div className="flex flex-wrap gap-2 mb-2">
        <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">
          {primary.shot_type}
        </span>
        <span className="px-2 py-0.5 text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full">
          {primary.angle}
        </span>
        <span className="px-2 py-0.5 text-xs font-medium bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 rounded-full">
          {primary.movement}
        </span>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
        {primary.reasoning}
      </p>
    </div>
  );
}
