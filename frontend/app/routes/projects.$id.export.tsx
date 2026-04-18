import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import type { Project } from "~/lib/types";
import { getProject, exportStoryboard } from "~/lib/api";
import { MoodBadge } from "~/components/mood-badge";
import { buildAssetUrl } from "~/lib/urls";

export default function ExportStoryboard() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    getProject(id)
      .then(setProject)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  async function handleDownload() {
    if (!id) return;
    try {
      const blob = await exportStoryboard(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.title || "storyboard"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-space-950">
        <div className="holo-spinner" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-space-950">
        <p className="text-gray-500 font-display tracking-wider">Project not found</p>
      </div>
    );
  }

  const lockedScenes = project.scenes.filter((s) => s.locked);

  return (
    <div className="min-h-screen bg-space-950">
      {/* ── Header ── */}
      <header className="border-b border-sand-600/20 bg-white/40 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate(`/projects/${id}`)}
              className="text-sm text-sand-600 hover:text-sand-800 font-display tracking-wider mb-1"
            >
              ← Back to workspace
            </button>
            <h1 className="text-xl font-display text-sand-800 tracking-wider">
              {project.title} — Storyboard
            </h1>
          </div>
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-sand-700 text-white border border-sand-600 text-sm rounded font-display tracking-wider hover:bg-sand-800 transition-all"
          >
            Download PDF
          </button>
        </div>
      </header>

      {/* ── Storyboard Grid ── */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {lockedScenes.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-sand-600/20 rounded-xl">
            <p className="text-stone-500">
              No locked scenes yet. Go back and lock some scenes to build your storyboard.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {lockedScenes.map((scene) => (
              <div
                key={scene.id}
                className="comic-panel bg-white/30 border border-sand-600/15 overflow-hidden"
              >
                {/* Sketch */}
                {scene.current_iteration?.sketch_url && (
                  <img
                    src={buildAssetUrl(scene.current_iteration.sketch_url)}
                    alt={scene.heading || "Scene sketch"}
                    className="w-full h-56 object-cover"
                  />
                )}
                {/* Info */}
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-stone-500">#{scene.scene_number}</span>
                    {scene.mood && <MoodBadge mood={scene.mood} size="sm" />}
                  </div>
                  <h3 className="font-display text-sand-800 text-sm tracking-wider">
                    {scene.heading || "Untitled"}
                  </h3>
                  <p className="text-xs text-stone-600 mt-1 line-clamp-3">
                    {scene.visual_summary || scene.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
