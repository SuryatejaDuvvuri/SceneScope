import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import type { Project, Scene } from "~/lib/types";
import { getProject, createScenes, refineScene, lockScene } from "~/lib/api";
import { SceneCard } from "~/components/scene-card";
import { SceneEditor } from "~/components/scene-editor";

export default function ProjectWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const [scriptInput, setScriptInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [refining, setRefining] = useState(false);

  // ── Load Project ──
  useEffect(() => {
    if (!id) return;
    getProject(id)
      .then((p) => {
        setProject(p);
        if (p.scenes.length > 0) {
          setSelectedSceneId(p.scenes[0].id);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  // ── Analyze Screenplay ──
  async function handleAnalyze() {
    if (!id || !scriptInput.trim()) return;
    setAnalyzing(true);
    try {
      const result = await createScenes(id, { text: scriptInput });
      // Reload project to get updated scenes
      const updated = await getProject(id);
      setProject(updated);
      if (updated.scenes.length > 0) {
        setSelectedSceneId(updated.scenes[0].id);
      }
      setScriptInput("");
    } catch (err) {
      console.error("Failed to analyze:", err);
    } finally {
      setAnalyzing(false);
    }
  }

  // ── Refine Scene ──
  async function handleRefine(sceneId: string, answers: Record<string, string>, feedback: string) {
    setRefining(true);
    try {
      const updatedScene = await refineScene(sceneId, { answers, feedback });
      // Update scene in project state
      setProject((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          scenes: prev.scenes.map((s) => (s.id === sceneId ? updatedScene : s)),
        };
      });
    } catch (err) {
      console.error("Failed to refine:", err);
    } finally {
      setRefining(false);
    }
  }

  // ── Lock Scene ──
  async function handleLock(sceneId: string) {
    try {
      const updatedScene = await lockScene(sceneId);
      setProject((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          scenes: prev.scenes.map((s) => (s.id === sceneId ? updatedScene : s)),
        };
      });
    } catch (err) {
      console.error("Failed to lock:", err);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <p className="text-gray-400 dark:text-gray-500">Loading project...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <p className="text-gray-400 dark:text-gray-500">Project not found</p>
      </div>
    );
  }

  const selectedScene = project.scenes.find((s) => s.id === selectedSceneId) || null;
  const lockedCount = project.scenes.filter((s) => s.locked).length;

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-950">
      {/* ── Top Bar ── */}
      <header className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          >
            ←
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">{project.title}</h1>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {project.genre}{project.time_period ? ` · ${project.time_period}` : ""}
              {project.scenes.length > 0 ? ` · ${project.scenes.length} scenes` : ""}
            </p>
          </div>
        </div>
        {lockedCount > 0 && (
          <button
            onClick={() => navigate(`/projects/${project.id}/export`)}
            className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            Export Storyboard ({lockedCount})
          </button>
        )}
      </header>

      {/* ── Main Layout ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Left Sidebar: Scene List + Input ── */}
        <aside className="w-72 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
          {/* Script Input */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-800">
            <textarea
              value={scriptInput}
              onChange={(e) => setScriptInput(e.target.value)}
              disabled={analyzing}
              rows={5}
              placeholder="Paste your screenplay here...&#10;&#10;INT. COFFEE SHOP - NIGHT&#10;A dimly lit coffee shop..."
              className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 resize-none"
            />
            <button
              onClick={handleAnalyze}
              disabled={analyzing || !scriptInput.trim()}
              className="mt-2 w-full px-3 py-2 bg-blue-600 text-white text-sm rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {analyzing ? "Analyzing..." : "Analyze Scenes"}
            </button>
          </div>

          {/* Scene List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {project.scenes.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-8">
                Paste a screenplay above to get started
              </p>
            ) : (
              project.scenes.map((scene) => (
                <SceneCard
                  key={scene.id}
                  scene={scene}
                  selected={scene.id === selectedSceneId}
                  onClick={() => setSelectedSceneId(scene.id)}
                />
              ))
            )}
          </div>
        </aside>

        {/* ── Main Area: Scene Editor ── */}
        <main className="flex-1 bg-white dark:bg-gray-900 overflow-hidden">
          {selectedScene ? (
            <SceneEditor
              scene={selectedScene}
              onRefine={handleRefine}
              onLock={handleLock}
              refining={refining}
            />
          ) : (
            <div className="h-full flex items-center justify-center">
              <p className="text-gray-400 dark:text-gray-500">
                {project.scenes.length === 0
                  ? "Paste a screenplay to start visualizing"
                  : "Select a scene from the sidebar"}
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
