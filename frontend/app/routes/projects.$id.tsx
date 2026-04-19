import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router";
import type { Project } from "~/lib/types";
import { getProject, createScenes, refineScene, lockScene, resetScenes } from "~/lib/api";
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
  const [inputExpanded, setInputExpanded] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Load Project ──
  useEffect(() => {
    if (!id) return;
    getProject(id)
      .then((p) => {
        setProject(p);
        if (p.scenes.length > 0) {
          setSelectedSceneId(p.scenes[0].id);
        } else {
          setInputExpanded(true); // auto-expand when no scenes yet
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  // ── Import File ──
  function handleFileImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) {
        setScriptInput(text);
        setInputExpanded(true);
      }
    };
    reader.readAsText(file);
    // Reset so same file can be re-imported
    e.target.value = "";
  }

  // ── Analyze Screenplay ──
  async function handleAnalyze() {
    if (!id || !scriptInput.trim()) return;
    setAnalyzing(true);
    try {
      await createScenes(id, { text: scriptInput });
      const updated = await getProject(id);
      setProject(updated);
      if (updated.scenes.length > 0) {
        setSelectedSceneId(updated.scenes[0].id);
      }
      setScriptInput("");
      setInputExpanded(false);
    } catch (err) {
      console.error("Failed to analyze:", err);
    } finally {
      setAnalyzing(false);
    }
  }

  // ── Reset Scenes ──
  async function handleReset() {
    if (!id) return;
    try {
      await resetScenes(id);
      const updated = await getProject(id);
      setProject(updated);
      setSelectedSceneId(null);
      setInputExpanded(true);
      setConfirmReset(false);
    } catch (err) {
      console.error("Failed to reset:", err);
    }
  }

  // ── Refine Scene ──
  async function handleRefine(sceneId: string, answers: Record<string, string>, feedback: string) {
    setRefining(true);
    try {
      const updatedScene = await refineScene(sceneId, { answers, feedback });
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
      <div className="min-h-screen flex items-center justify-center bg-space-950">
        <div className="holo-spinner" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-space-950">
        <p className="text-stone-500 font-display tracking-wider">Project not found</p>
      </div>
    );
  }

  const selectedScene = project.scenes.find((s) => s.id === selectedSceneId) || null;
  const lockedCount = project.scenes.filter((s) => s.locked).length;
  const hasScenes = project.scenes.length > 0;

  return (
    <div className="h-screen flex flex-col bg-space-950">
      {/* ── Top Bar ── */}
      <header className="flex items-center justify-between px-6 py-4 bg-space-900/85 border-b border-sand-600/20 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="text-sm text-sand-700 hover:text-sand-900 font-display transition-colors"
          >
            ←
          </button>
          <div>
            <h1 className="font-display text-2xl font-semibold text-sand-800">{project.title}</h1>
            <p className="text-sm text-stone-500 font-mono">
              {project.genre}{project.time_period ? ` · ${project.time_period}` : ""}
              {hasScenes ? ` · ${project.scenes.length} scenes` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {hasScenes && (
            <>
              {confirmReset ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-500 font-mono">Reset all scenes?</span>
                  <button
                    onClick={handleReset}
                    className="px-3 py-1.5 text-xs bg-red-600 text-white rounded font-display hover:bg-red-700 transition-all"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setConfirmReset(false)}
                    className="px-3 py-1.5 text-xs bg-stone-200 text-stone-700 rounded font-display hover:bg-stone-300 transition-all"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmReset(true)}
                  className="text-xs text-stone-400 hover:text-stone-600 font-mono transition-colors"
                >
                  Reset scenes
                </button>
              )}
            </>
          )}
          {lockedCount > 0 && (
            <button
              onClick={() => navigate(`/projects/${project.id}/export`)}
              className="px-4 py-2 text-sm bg-sand-700 text-white border border-sand-600 rounded font-display hover:bg-sand-800 transition-all"
            >
              Export Storyboard ({lockedCount})
            </button>
          )}
        </div>
      </header>

      {/* ── Script Input Area ── */}
      {hasScenes ? (
        /* Collapsed bar when scenes exist */
        <div className="border-b border-sand-600/15 bg-space-900/55">
          {inputExpanded ? (
            <div className="px-6 py-5">
              <div className="flex gap-3 items-start">
                <div className="flex-1 flex flex-col gap-2">
                  <textarea
                    value={scriptInput}
                    onChange={(e) => setScriptInput(e.target.value)}
                    disabled={analyzing}
                    rows={5}
                    placeholder={"Paste additional screenplay scenes here...\n\nINT. COFFEE SHOP - NIGHT\nA dimly lit coffee shop, rain streaking the windows..."}
                    className="w-full px-4 py-3 text-sm bg-white/70 border border-sand-600/25 rounded-lg text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40 disabled:opacity-50 resize-none leading-relaxed font-mono"
                  />
                  <div className="flex items-center gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".fountain,.txt,.fdx"
                      onChange={handleFileImport}
                      className="hidden"
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="px-3 py-1.5 text-xs bg-white/60 border border-sand-600/20 text-sand-700 rounded font-display hover:bg-white/80 transition-all"
                    >
                      Import file (.fountain, .txt, .fdx)
                    </button>
                    <span className="text-xs text-stone-400 font-mono">Fountain format recommended</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <button
                    onClick={handleAnalyze}
                    disabled={analyzing || !scriptInput.trim()}
                    className="px-5 py-2.5 bg-sand-700 text-white border border-sand-600 text-sm rounded-lg font-display whitespace-nowrap hover:bg-sand-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {analyzing ? "Analyzing..." : "Analyze"}
                  </button>
                  <button
                    onClick={() => { setInputExpanded(false); setScriptInput(""); }}
                    className="px-5 py-2 text-xs bg-white/40 border border-sand-600/15 text-stone-500 rounded-lg font-mono hover:bg-white/60 transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between px-6 py-3">
              <span className="text-xs text-stone-500 font-mono">
                {project.scenes.length} scenes loaded
              </span>
              <button
                onClick={() => setInputExpanded(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white/40 border border-sand-600/20 text-sand-700 rounded font-display hover:bg-white/70 transition-all"
              >
                <span>+</span> Add more scenes
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Full input panel when no scenes */
        <div className="px-6 py-6 bg-space-900/60 border-b border-sand-600/15">
          <div className="flex gap-4 items-start max-w-full">
            <div className="flex-1 flex flex-col gap-2">
              <textarea
                value={scriptInput}
                onChange={(e) => setScriptInput(e.target.value)}
                disabled={analyzing}
                rows={5}
                placeholder={"Paste your screenplay here...\n\nINT. COFFEE SHOP - NIGHT\nA dimly lit coffee shop, rain streaking the windows...\n\nEXT. ALLEY - NIGHT\n..."}
                className="w-full px-4 py-3 text-sm bg-white/70 border border-sand-600/25 rounded-lg text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40 disabled:opacity-50 resize-none leading-relaxed font-mono"
              />
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".fountain,.txt,.fdx"
                  onChange={handleFileImport}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 text-xs bg-white/60 border border-sand-600/20 text-sand-700 rounded font-display hover:bg-white/80 transition-all"
                >
                  Import file (.fountain, .txt, .fdx)
                </button>
                <span className="text-xs text-stone-400 font-mono">or paste Fountain-formatted text above</span>
              </div>
            </div>
            <button
              onClick={handleAnalyze}
              disabled={analyzing || !scriptInput.trim()}
              className="px-6 py-3 bg-sand-700 text-white border border-sand-600 text-sm rounded-lg font-display whitespace-nowrap hover:bg-sand-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {analyzing ? "Analyzing..." : "Analyze Scenes"}
            </button>
          </div>
        </div>
      )}

      {/* ── Horizontal Scene Strip ── */}
      {hasScenes && (
        <div className="border-b border-sand-600/15 bg-space-900/45">
          <div className="flex items-center gap-2 px-6 py-3 overflow-x-auto scrollbar-thin">
            {project.scenes.map((scene) => (
              <SceneCard
                key={scene.id}
                scene={scene}
                selected={scene.id === selectedSceneId}
                onClick={() => setSelectedSceneId(scene.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Main Area: Scene Editor ── */}
      <main className="flex-1 bg-space-950 overflow-hidden">
        {analyzing ? (
          <div className="h-full flex flex-col items-center justify-center gap-4">
            <div className="holo-spinner" />
            <p className="text-sm text-stone-500 font-mono">Parsing scenes, classifying mood, generating sketches...</p>
            <p className="text-xs text-stone-400 font-mono">This may take a minute for long screenplays</p>
          </div>
        ) : selectedScene ? (
          <SceneEditor
            scene={selectedScene}
            onRefine={handleRefine}
            onLock={handleLock}
            refining={refining}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center gap-3">
            <p className="text-stone-500 font-mono text-base">
              {!hasScenes ? "Import or paste a screenplay to start" : "Select a scene above"}
            </p>
            {!hasScenes && (
              <p className="text-xs text-stone-400 font-mono max-w-sm text-center">
                Fountain format works best. Each INT./EXT. heading becomes a scene.
              </p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
