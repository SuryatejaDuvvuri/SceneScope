import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import type { Project } from "~/lib/types";
import { getProject, exportStoryboard } from "~/lib/api";
import { MoodBadge } from "~/components/mood-badge";

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
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <p className="text-gray-400">Loading...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <p className="text-gray-400">Project not found</p>
      </div>
    );
  }

  const lockedScenes = project.scenes.filter((s) => s.locked);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* ── Header ── */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate(`/projects/${id}`)}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 mb-1"
            >
              ← Back to workspace
            </button>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {project.title} — Storyboard
            </h1>
          </div>
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Download PDF
          </button>
        </div>
      </header>

      {/* ── Storyboard Grid ── */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {lockedScenes.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-xl">
            <p className="text-gray-500 dark:text-gray-400">
              No locked scenes yet. Go back and lock some scenes to build your storyboard.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {lockedScenes.map((scene) => (
              <div
                key={scene.id}
                className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden"
              >
                {/* Sketch */}
                {scene.current_iteration?.sketch_url && (
                  <img
                    src={scene.current_iteration.sketch_url}
                    alt={scene.heading || "Scene sketch"}
                    className="w-full h-56 object-cover"
                  />
                )}
                {/* Info */}
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-gray-400">#{scene.scene_number}</span>
                    {scene.mood && <MoodBadge mood={scene.mood} size="sm" />}
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                    {scene.heading || "Untitled"}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-3">
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
