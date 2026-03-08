import type { Scene } from "~/lib/types";
import { MoodBadge } from "./mood-badge";

interface SceneCardProps {
  scene: Scene;
  selected: boolean;
  onClick: () => void;
}

export function SceneCard({ scene, selected, onClick }: SceneCardProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-colors ${
        selected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
          : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-mono text-gray-400 dark:text-gray-500">
          #{scene.scene_number}
        </span>
        <div className="flex items-center gap-1.5">
          {scene.locked && (
            <span className="text-xs text-green-600 dark:text-green-400">✓ Locked</span>
          )}
          {scene.mood && <MoodBadge mood={scene.mood} size="sm" />}
        </div>
      </div>
      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
        {scene.heading || "Untitled Scene"}
      </p>
      {scene.current_iteration?.sketch_url && (
        <img
          src={scene.current_iteration.sketch_url}
          alt="Scene sketch"
          className="mt-2 w-full h-16 object-cover rounded border border-gray-200 dark:border-gray-700"
        />
      )}
    </button>
  );
}
