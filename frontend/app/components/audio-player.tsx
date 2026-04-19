import React, { useEffect, useRef, useState } from "react";
import type { DialogueLine, SceneAudio } from "~/lib/types";
import { generateSceneAudio, getSceneAudio } from "~/lib/api";
import { buildAssetUrl } from "~/lib/urls";

interface AudioPlayerProps {
  sceneId: string;
  dialogue: DialogueLine[];
}

export function AudioPlayer({ sceneId, dialogue }: AudioPlayerProps) {
  const [audio, setAudio] = useState<SceneAudio | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Fetch existing audio on mount
  useEffect(() => {
    let cancelled = false;
    getSceneAudio(sceneId)
      .then((data) => {
        if (!cancelled && data) setAudio(data);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [sceneId]);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateSceneAudio(sceneId);
      setAudio(result);
    } catch (e: any) {
      setError(e.message || "Failed to generate audio");
    } finally {
      setLoading(false);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const pct = (audioRef.current.currentTime / audioRef.current.duration) * 100;
    setProgress(isNaN(pct) ? 0 : pct);
  };

  const handleEnded = () => {
    setPlaying(false);
    setProgress(0);
  };

  if (!dialogue || dialogue.length === 0) return null;

  return (
    <div className="w-full rounded-xl border border-sand-600/20 bg-white/65 p-5">
      <h4 className="text-sm font-display text-sand-700 mb-3">Scene Dialogue</h4>

      {/* Dialogue transcript */}
      <div className="space-y-3 mb-5 max-h-56 overflow-y-auto pr-1">
        {dialogue.map((line, i) => (
          <div key={i} className="text-sm">
            <span className="font-semibold text-sand-800">{line.character}</span>
            {line.parenthetical && (
              <span className="text-stone-400 italic ml-1">({line.parenthetical})</span>
            )}
            <p className="text-stone-700 ml-4 leading-relaxed">{line.text}</p>
          </div>
        ))}
      </div>

      {/* Audio controls */}
      {audio ? (
        <div className="flex items-center gap-3">
          <audio
            ref={audioRef}
            src={buildAssetUrl(audio.audio_url)}
            onTimeUpdate={handleTimeUpdate}
            onEnded={handleEnded}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
          />
          <button
            onClick={togglePlay}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-sand-700 text-white hover:bg-sand-800 transition-colors shrink-0"
          >
            {playing ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <rect x="2" y="1" width="4" height="12" rx="1" />
                <rect x="8" y="1" width="4" height="12" rx="1" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <polygon points="2,1 12,7 2,13" />
              </svg>
            )}
          </button>
          <div className="flex-1 h-2 bg-sand-600/15 rounded-full overflow-hidden">
            <div
              className="h-full bg-sand-700 rounded-full transition-all duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-xs text-stone-500 font-mono">
            {audio.total_duration_ms ? `${Math.round(audio.total_duration_ms / 1000)}s` : ""}
          </span>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="text-xs text-sand-700 hover:text-sand-900 font-mono disabled:opacity-50"
          >
            Regenerate
          </button>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-2 bg-sand-600/10 text-sand-800 border border-sand-600/25 text-sm rounded font-display hover:bg-sand-600/20 transition-all disabled:opacity-50"
        >
          {loading ? "Generating audio..." : "Generate Dialogue Audio"}
        </button>
      )}

      {error && (
        <p className="text-xs text-red-500 mt-2">{error}</p>
      )}
    </div>
  );
}
