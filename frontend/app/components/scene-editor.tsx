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
      <div className="flex items-center justify-between px-6 py-4 border-b border-sand-600/20 bg-space-900/50 poof">
        <div>
          <h2 className="text-xl font-display text-sand-800 glow-text-sand">
            {scene.heading || `Scene ${scene.scene_number}`}
          </h2>
          <div className="flex items-center gap-2 mt-1">
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
            className="px-4 py-2 bg-sand-700 text-white border border-sand-600 text-sm rounded font-display hover:bg-sand-800 transition-all disabled:opacity-50"
          >
            Lock Scene ✓
          </button>
        ) : (
          <span className="px-4 py-2 bg-sand-600/15 text-sand-800 border border-sand-600/30 text-sm rounded font-display">
            Locked ✓
          </span>
        )}
      </div>

      {/* ── Side-by-side: Description + Sketch + Iteration History ── */}
      <div className="flex-1 overflow-auto">
        {/* Iteration History Bar */}
        <div className="flex items-center gap-2 px-6 py-2 border-b border-sand-600/10 bg-space-900/30">
          <span className="text-sm text-stone-500 font-mono">History:</span>
          {scene.iterations.map((it) => (
            <button
              key={it.iteration_number}
              onClick={() => setSelectedIteration(it.iteration_number)}
              className={`px-2 py-1 rounded text-xs font-mono border ${selectedIteration === it.iteration_number ? 'bg-sand-600/20 text-sand-800 border-sand-500/40' : 'bg-white/40 text-stone-600 border-sand-600/15 hover:border-sand-500/30'} transition-colors`}
            >
              {it.iteration_number}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 h-full">
          {/* ── Left: Description + Controls + Iteration Details ── */}
          <div className="p-6 border-r border-sand-600/15 overflow-y-auto space-y-4">
            {/* Scene Description */}
            <div>
              <h3 className="text-base font-display text-sand-700 mb-2">
                Scene Description
              </h3>
              <p className="text-base text-stone-600 leading-relaxed whitespace-pre-wrap">
                {scene.description}
              </p>
            </div>

            {/* Iteration Details */}
            {selected && (
              <div className="mb-4">
                <h4 className="text-sm font-display text-sand-700 mb-1">Refinement #{selected.iteration_number}</h4>
                {selected.answers && (
                  <div className="mb-3">
                    <div className="text-sm text-stone-500 font-mono mb-1">Answers:</div>
                    <ul className="text-sm text-stone-700 space-y-1">
                      {Object.entries(selected.answers).map(([q, a]) => (
                        <li key={q}><span className="font-semibold text-sand-700">{q}:</span> {a}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {selected.feedback && (
                  <div className="mb-3">
                    <div className="text-sm text-stone-500 font-mono mb-1">Feedback:</div>
                    <div className="text-sm text-stone-700">{selected.feedback}</div>
                  </div>
                )}
                {selected.director_notes && (
                  <div className="mb-3">
                    <div className="text-sm text-stone-500 font-mono mb-1">Director Notes:</div>
                    <div className="text-sm text-stone-700">{selected.director_notes.interpretation}</div>
                  </div>
                )}
              </div>
            )}

            {/* Visual Summary */}
            {scene.visual_summary && (
              <div>
                <h3 className="text-base font-display text-sand-700 mb-1">
                  Visual Summary
                </h3>
                <p className="text-base text-stone-500 italic leading-relaxed">
                  {scene.visual_summary}
                </p>
              </div>
            )}

            {/* Shot Suggestions */}
            {scene.shot_suggestions && <ShotInfo shots={scene.shot_suggestions} />}

            {/* Vague Elements */}
            {scene.vague_elements.length > 0 && (
              <div>
                <h3 className="text-base font-display text-sand-700 mb-1">
                  Vague Elements
                </h3>
                <ul className="space-y-1.5">
                  {scene.vague_elements.map((el, i) => (
                    <li
                      key={i}
                      className="text-base text-sand-700 flex items-start gap-1.5"
                    >
                      <span className="mt-0.5">⚠</span> {el}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Clarifying Questions + Refinement */}
            {canRefine && (
              <ClarifyingQuestions
                questions={scene.clarifying_questions}
                onSubmit={(answers, feedback) => onRefine(scene.id, answers, feedback)}
                disabled={refining}
                remainingAttempts={remainingAttempts}
              />
            )}

            {!canRefine && !scene.locked && (
              <p className="text-base text-stone-500 italic">
                No refinements remaining. Lock the scene to finalize.
              </p>
            )}
          </div>

          {/* ── Right: Sketch + Audio ── */}
          <div className="p-6 bg-space-800/40 flex flex-col gap-6 overflow-y-auto sparkle-particles">
            {refining ? (
              <div className="text-center space-y-3 flex-1 flex flex-col items-center justify-center">
                <div className="holo-spinner mx-auto" />
                <p className="text-sm text-stone-500 font-mono">Generating sketch...</p>
              </div>
            ) : sketchUrl ? (
              <div className="w-full">
                <img
                  src={sketchUrl}
                  alt={`Sketch for ${scene.heading}`}
                  className="w-full rounded border border-sand-600/25 shadow-lg shadow-sand-300/20"
                />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center">
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
