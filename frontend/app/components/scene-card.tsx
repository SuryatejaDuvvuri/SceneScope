import type { Scene } from "~/lib/types";
import { MoodBadge } from "./mood-badge";
import { buildAssetUrl } from "~/lib/urls";

interface SceneCardProps {
  scene: Scene;
  selected: boolean;
  onClick: () => void;
}

export function SceneCard({ scene, selected, onClick }: SceneCardProps) {
  return (
    <button
      onClick={onClick}
      className={`flex-shrink-0 flex items-center gap-3 px-4 py-2.5 rounded-lg border transition-all ${
        selected
          ? "border-sand-500/50 bg-sand-500/15 shadow-sm shadow-sand-400/20"
          : "border-sand-600/15 bg-white/40 hover:border-sand-500/30 hover:bg-white/60"
      }`}
    >
      {/* Thumbnail */}
      {scene.current_iteration?.sketch_url && (
        <img
          src={buildAssetUrl(scene.current_iteration.sketch_url)}
          alt="Scene sketch"
          className="w-12 h-8 object-cover rounded border border-sand-600/20 flex-shrink-0"
        />
      )}
      <div className="text-left min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-mono text-stone-500">
            #{scene.scene_number}
          </span>
          {scene.locked && (
            <span className="text-xs text-sand-700 font-mono">✓</span>
          )}
          {scene.mood && <MoodBadge mood={scene.mood} size="sm" />}
        </div>
        <p className="text-sm font-medium text-sand-800 truncate max-w-[140px]">
          {scene.heading || "Untitled Scene"}
        </p>
      </div>
    </button>
  );
}
