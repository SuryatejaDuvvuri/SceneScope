import React, { useEffect, useState } from "react";
import type { Scene } from "~/lib/types";
import { MoodBadge } from "./mood-badge";
import { ShotInfo } from "./shot-info";
import { ClarifyingQuestions } from "./clarifying-questions";
import { AudioPlayer } from "./audio-player";

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
    // If scene changes, reset to latest with sketch or latest iteration
    setSelectedIteration(
      scene.current_iteration?.iteration_number
      || latestWithSketch?.iteration_number
      || scene.iterations.length
      || 1
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene.id]);
  const selected = scene.iterations.find((it) => it.iteration_number === selectedIteration) || scene.current_iteration;
  const sketchUrl = selected?.sketch_url;

  return (
    <div className="h-full flex flex-col">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {scene.heading || `Scene ${scene.scene_number}`}
          </h2>
          <div className="flex items-center gap-2 mt-1">
            {scene.mood && <MoodBadge mood={scene.mood} confidence={scene.mood_confidence} />}
            <span className="text-xs text-gray-400 dark:text-gray-500">
              Iteration {iterationCount}
            </span>
          </div>
        </div>
        {!scene.locked ? (
          <button
            onClick={() => onLock(scene.id)}
            disabled={refining}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            Lock Scene ✓
          </button>
        ) : (
          <span className="px-4 py-2 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-sm rounded-lg font-medium">
            Locked ✓
          </span>
        )}
      </div>

      {/* ── Side-by-side: Description + Sketch + Iteration History ── */}
      <div className="flex-1 overflow-auto">
        {/* Iteration History Bar */}
        <div className="flex items-center gap-2 px-6 py-2 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/30">
          <span className="text-xs text-gray-400">History:</span>
          {scene.iterations.map((it) => (
            <button
              key={it.iteration_number}
              onClick={() => setSelectedIteration(it.iteration_number)}
              className={`px-2 py-1 rounded text-xs font-mono border ${selectedIteration === it.iteration_number ? 'bg-blue-600 text-white border-blue-700' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-700'} transition-colors`}
            >
              {it.iteration_number}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 h-full">
          {/* ── Left: Description + Controls + Iteration Details ── */}
          <div className="p-6 border-r border-gray-200 dark:border-gray-800 overflow-y-auto space-y-4">
            {/* Scene Description */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Scene Description
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-wrap">
                {scene.description}
              </p>
            </div>

            {/* Iteration Details */}
            {selected && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Refinement #{selected.iteration_number}</h4>
                {selected.answers && (
                  <div className="mb-2">
                    <div className="text-xs text-gray-400 mb-1">Answers:</div>
                    <ul className="text-xs text-gray-700 dark:text-gray-300 space-y-1">
                      {Object.entries(selected.answers).map(([q, a]) => (
                        <li key={q}><span className="font-semibold">{q}:</span> {a}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {selected.feedback && (
                  <div className="mb-2">
                    <div className="text-xs text-gray-400 mb-1">Feedback:</div>
                    <div className="text-xs text-gray-700 dark:text-gray-300">{selected.feedback}</div>
                  </div>
                )}
                {selected.director_notes && (
                  <div className="mb-2">
                    <div className="text-xs text-gray-400 mb-1">Director Notes:</div>
                    <div className="text-xs text-gray-700 dark:text-gray-300">{selected.director_notes.interpretation}</div>
                  </div>
                )}
              </div>
            )}

            {/* Visual Summary */}
            {scene.visual_summary && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Visual Summary
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 italic leading-relaxed">
                  {scene.visual_summary}
                </p>
              </div>
            )}

            {/* Shot Suggestions */}
            {scene.shot_suggestions && <ShotInfo shots={scene.shot_suggestions} />}

            {/* Vague Elements */}
            {scene.vague_elements.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Vague Elements
                </h3>
                <ul className="space-y-1">
                  {scene.vague_elements.map((el, i) => (
                    <li
                      key={i}
                      className="text-sm text-amber-600 dark:text-amber-400 flex items-start gap-1.5"
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
                questions={selected?.clarifying_questions || scene.clarifying_questions}
                onSubmit={(answers, feedback) => onRefine(scene.id, answers, feedback)}
                disabled={refining}
                remainingAttempts={remainingAttempts}
              />
            )}

            {!canRefine && !scene.locked && (
              <p className="text-sm text-gray-400 dark:text-gray-500 italic">
                No refinements remaining. Lock the scene to finalize.
              </p>
            )}
          </div>

          {/* ── Right: Sketch ── */}
          <div className="p-6 bg-gray-50 dark:bg-gray-900/50 flex flex-col items-center justify-center overflow-y-auto">
            {refining ? (
              <div className="text-center space-y-3">
                <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 rounded-full animate-spin mx-auto" />
                <p className="text-sm text-gray-500 dark:text-gray-400">Generating sketch...</p>
              </div>
            ) : sketchUrl ? (
              <div className="w-full">
                <img
                  src={sketchUrl}
                  alt={`Sketch for ${scene.heading}`}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm"
                />
              </div>
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500">No sketch generated yet</p>
            )}

            <div className="w-full">
              <AudioPlayer sceneId={scene.id} dialogue={scene.dialogue || []} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
