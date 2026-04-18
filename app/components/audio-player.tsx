import { useEffect, useMemo, useRef, useState } from "react";
import type { DialogueLine, SceneAudio } from "~/lib/types";
import { generateSceneAudio, getSceneAudio } from "~/lib/api";

interface AudioPlayerProps {
  sceneId: string;
  dialogue: DialogueLine[];
}

function formatMs(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function AudioPlayer({ sceneId, dialogue }: AudioPlayerProps) {
  const [audio, setAudio] = useState<SceneAudio | null>(null);
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [progressMs, setProgressMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const hasDialogue = (dialogue?.length || 0) > 0;
  const durationMs = audio ? audio.total_duration_ms : 0;
  const progressPct = durationMs > 0 ? Math.min(100, (progressMs / durationMs) * 100) : 0;

  useEffect(() => {
    let cancelled = false;
    setAudio(null);
    setPlaying(false);
    setProgressMs(0);
    setError(null);

    if (!hasDialogue) return;

    (async () => {
      try {
        const existing = await getSceneAudio(sceneId);
        if (!cancelled) setAudio(existing);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load audio");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sceneId, hasDialogue]);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;

    const onTime = () => setProgressMs(el.currentTime * 1000);
    const onEnded = () => setPlaying(false);
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("ended", onEnded);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("ended", onEnded);
    };
  }, [audio?.audio_url]);

  const transcript = useMemo(
    () => (audio?.dialogue_data?.length ? audio.dialogue_data : dialogue || []),
    [audio?.dialogue_data, dialogue]
  );

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const generated = await generateSceneAudio(sceneId);
      setAudio(generated);
      setProgressMs(0);
      setPlaying(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate audio");
    } finally {
      setLoading(false);
    }
  }

  async function handleTogglePlay() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
      return;
    }
    try {
      await el.play();
      setPlaying(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Playback failed");
    }
  }

  if (!hasDialogue) {
    return (
      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-900">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Dialogue Audio</h4>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          No parsed dialogue found for this scene.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-900">
      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Dialogue Audio</h4>

      {audio?.audio_url ? (
        <div className="mt-3 space-y-2">
          <audio ref={audioRef} src={audio.audio_url} preload="metadata" />
          <div className="flex items-center gap-2">
            <button
              onClick={handleTogglePlay}
              className="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              {playing ? "Pause" : "Play"}
            </button>
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="px-3 py-1.5 text-xs rounded bg-gray-200 dark:bg-gray-800 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              {loading ? "Regenerating..." : "Regenerate"}
            </button>
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
              {formatMs(progressMs)} / {formatMs(durationMs)}
            </span>
          </div>
          <div className="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded">
            <div className="h-2 bg-blue-500 rounded" style={{ width: `${progressPct}%` }} />
          </div>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="mt-3 px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Generating Audio..." : "Generate Audio"}
        </button>
      )}

      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}

      <div className="mt-3 max-h-40 overflow-auto rounded border border-gray-100 dark:border-gray-800 p-2 bg-gray-50 dark:bg-gray-950">
        {transcript.map((line, i) => (
          <p key={`${line.character}-${i}`} className="text-xs text-gray-700 dark:text-gray-300 mb-1">
            <span className="font-semibold">{line.character}:</span> {line.text}
          </p>
        ))}
      </div>
    </div>
  );
}
