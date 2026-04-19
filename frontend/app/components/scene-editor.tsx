import React, { useEffect, useState } from "react";
import type { Scene } from "~/lib/types";
import { MoodBadge } from "./mood-badge";
import { ShotInfo } from "./shot-info";
import { ClarifyingQuestions } from "./clarifying-questions";
import { AudioPlayer } from "./audio-player";
import { buildAssetUrl } from "~/lib/urls";

const MAX_REFINEMENTS = 3;

interface SceneEditorProps {
  scene: Scene;
  onRefine: (sceneId: string, answers: Record<string, string>, feedback: string) => void;
  onLock: (sceneId: string) => void;
  refining: boolean;
}

export function SceneEditor({ scene, onRefine, onLock, refining }: SceneEditorProps) {
  const iterationCount = scene.iterations.length;
  const remainingAttempts = MAX_REFINEMENTS - iterationCount + 1;
  const canRefine = !scene.locked && remainingAttempts > 0;
  // Refinement history navigation
  // Find the latest iteration with a sketch, or fallback to the latest iteration
  const latestWithSketch = [...scene.iterations].reverse().find(it => it.sketch_url) || scene.iterations[scene.iterations.length - 1] || null;
  const [selectedIteration, setSelectedIteration] = useState<number>(
    scene.current_iteration?.iteration_number
    || latestWithSketch?.iteration_number
    || scene.iterations.length
    || 1
  );
  useEffect(() => {
    // Reset to latest iteration when the scene changes OR when a new iteration
    // is added (e.g. right after a refine completes).
    setSelectedIteration(
      scene.current_iteration?.iteration_number
      || latestWithSketch?.iteration_number
      || scene.iterations.length
      || 1
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene.id, scene.iterations.length, scene.current_iteration?.iteration_number]);
  const selected = scene.iterations.find((it) => it.iteration_number === selectedIteration) || scene.current_iteration;
  const sketchUrl = buildAssetUrl(selected?.sketch_url);

  return (
    <div className="h-full flex flex-col">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-start justify-between gap-4 px-8 py-5 border-b border-sand-600/20 bg-space-900/60">
        <div>
          <h2 className="text-2xl font-display text-sand-800">
            {scene.heading || `Scene ${scene.scene_number}`}
          </h2>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            {scene.mood && <MoodBadge mood={scene.mood} confidence={scene.mood_confidence} />}
            <span className="text-sm text-stone-500 font-mono">
              Iteration {iterationCount}
            </span>
          </div>
        </div>
        {!scene.locked ? (
          <button
            onClick={() => onLock(scene.id)}
            disabled={refining}
            className="px-4 py-2.5 bg-sand-700 text-white border border-sand-600 text-sm rounded-lg font-display hover:bg-sand-800 transition-all disabled:opacity-50"
          >
            Lock Scene ✓
          </button>
        ) : (
          <span className="px-4 py-2.5 bg-sand-600/15 text-sand-800 border border-sand-600/30 text-sm rounded-lg font-display">
            Locked ✓
          </span>
        )}
      </div>

      {/* ── Side-by-side: Description + Sketch + Iteration History ── */}
      <div className="flex-1 min-h-0 flex flex-col">
        {/* Iteration History Bar */}
        <div className="flex flex-wrap items-center gap-2 px-8 py-3 border-b border-sand-600/10 bg-space-900/40">
          <span className="text-sm text-stone-500 font-mono mr-1">History:</span>
          {scene.iterations.map((it) => (
            <button
              key={it.iteration_number}
              onClick={() => setSelectedIteration(it.iteration_number)}
              className={`px-2.5 py-1.5 rounded-md text-xs font-mono border ${selectedIteration === it.iteration_number ? "bg-sand-600/20 text-sand-800 border-sand-500/40" : "bg-white/50 text-stone-600 border-sand-600/15 hover:border-sand-500/30"} transition-colors`}
            >
              {it.iteration_number}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 p-6 xl:p-8 flex-1 min-h-0">
          {/* ── Left: Description + Controls + Iteration Details ── */}
          <div className="space-y-5 overflow-y-auto min-h-0 pr-1">
            {/* Scene Description */}
            <section className="rounded-xl border border-sand-600/20 bg-white/65 p-5">
              <h3 className="text-base font-display text-sand-700 mb-2">
                Scene Description
              </h3>
              <p className="text-base text-stone-700 leading-7 whitespace-pre-wrap">
                {scene.description}
              </p>
            </section>

            {/* Iteration Details */}
            {selected && (
              <section className="rounded-xl border border-sand-600/20 bg-white/65 p-5">
                <h4 className="text-sm font-display text-sand-700 mb-3">Refinement #{selected.iteration_number}</h4>
                {selected.answers && (
                  <div className="mb-4">
                    <div className="text-xs text-stone-500 font-mono mb-2 uppercase tracking-wide">Answers</div>
                    <ul className="text-sm text-stone-700 space-y-2">
                      {Object.entries(selected.answers).map(([q, a]) => (
                        <li key={q} className="leading-relaxed">
                          <span className="font-semibold text-sand-700">{q}:</span> {a}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {selected.feedback && (
                  <div className="mb-4">
                    <div className="text-xs text-stone-500 font-mono mb-2 uppercase tracking-wide">Feedback</div>
                    <div className="text-sm text-stone-700 leading-relaxed">{selected.feedback}</div>
                  </div>
                )}
                {selected.director_notes && (
                  <div>
                    <div className="text-xs text-stone-500 font-mono mb-2 uppercase tracking-wide">Director Notes</div>
                    <div className="text-sm text-stone-700 leading-relaxed">{selected.director_notes.interpretation}</div>
                  </div>
                )}
              </section>
            )}

            {/* Visual Summary */}
            {scene.visual_summary && (
              <section className="rounded-xl border border-sand-600/20 bg-white/65 p-5">
                <h3 className="text-base font-display text-sand-700 mb-2">
                  Visual Summary
                </h3>
                <p className="text-base text-stone-600 italic leading-7">
                  {scene.visual_summary}
                </p>
              </section>
            )}

            {/* Shot Suggestions */}
            {scene.shot_suggestions && (
              <section className="rounded-xl border border-sand-600/20 bg-white/65 p-5">
                <ShotInfo shots={scene.shot_suggestions} />
              </section>
            )}

            {/* Vague Elements */}
            {scene.vague_elements.length > 0 && (
              <section className="rounded-xl border border-sand-600/20 bg-white/65 p-5">
                <h3 className="text-base font-display text-sand-700 mb-2">
                  Vague Elements
                </h3>
                <ul className="space-y-2">
                  {scene.vague_elements.map((el, i) => (
                    <li
                      key={i}
                      className="text-base text-sand-700 flex items-start gap-2 leading-relaxed"
                    >
                      <span className="mt-0.5">⚠</span>
                      <span>{el}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Clarifying Questions + Refinement */}
            {canRefine && (
              <section className="rounded-xl border border-sand-600/20 bg-white/65 p-5">
                <ClarifyingQuestions
                  questions={scene.clarifying_questions}
                  onSubmit={(answers, feedback) => onRefine(scene.id, answers, feedback)}
                  disabled={refining}
                  remainingAttempts={remainingAttempts}
                />
              </section>
            )}

            {!canRefine && !scene.locked && (
              <p className="text-base text-stone-500 italic px-1">
                No refinements remaining. Lock the scene to finalize.
              </p>
            )}
          </div>

          {/* ── Right: Sketch + Audio ── */}
          <div className="space-y-5 overflow-y-auto min-h-0 pr-1">
            {refining ? (
              <div className="rounded-xl border border-sand-600/20 bg-white/65 p-8 text-center space-y-3 min-h-64 h-[min(52vh,520px)] flex flex-col items-center justify-center">
                <div className="holo-spinner mx-auto" />
                <p className="text-sm text-stone-500 font-mono">Generating sketch...</p>
              </div>
            ) : sketchUrl ? (
              <div className="w-full rounded-xl border border-sand-600/20 bg-white/65 p-4">
                <img
                  src={sketchUrl}
                  alt={`Sketch for ${scene.heading}`}
                  className="w-full h-[min(52vh,520px)] object-contain bg-black/90 rounded-lg border border-sand-600/25 shadow-lg shadow-sand-300/20"
                />
              </div>
            ) : (
              <div className="rounded-xl border border-sand-600/20 bg-white/65 p-8 flex items-center justify-center min-h-64 h-[min(52vh,520px)]">
                <p className="text-sm text-stone-500 font-mono">No sketch generated yet</p>
              </div>
            )}

            {/* ── Dialogue Audio ── */}
            {scene.dialogue && scene.dialogue.length > 0 && (
              <div className="w-full">
                <AudioPlayer sceneId={scene.id} dialogue={scene.dialogue} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
