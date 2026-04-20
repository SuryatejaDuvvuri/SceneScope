import { useState } from "react";
import { useNavigate } from "react-router";
import { createProject } from "~/lib/api";

const GENRES = ["Drama", "Thriller", "Comedy", "Horror", "Sci-Fi", "Action", "Romance", "Western"];

export default function NewProject() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");
  const [timePeriod, setTimePeriod] = useState("");
  const [tone, setTone] = useState("");
  const [filmsInput, setFilmsInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const films = filmsInput
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean);

      const project = await createProject({
        title: title.trim(),
        genre: genre || undefined,
        time_period: timePeriod || undefined,
        tone: tone || undefined,
        films,
      });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      console.error("Failed to create project:", err);
      setError(err instanceof Error ? err.message : "Failed to create project");
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-space-950">
      {/* ── Header ── */}
      <header className="border-b border-sand-600/20 bg-white/40 backdrop-blur-sm">
        <div className="max-w-2xl mx-auto px-6 py-6">
          <button
            onClick={() => navigate("/")}
            className="text-sm text-sand-600 hover:text-sand-800 font-display tracking-wider mb-2"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-display text-sand-800 tracking-wider">New Project</h1>
        </div>
      </header>

      {/* ── Form ── */}
      <main className="max-w-2xl mx-auto px-6 py-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="px-3 py-2 rounded border border-red-300/70 bg-red-50/70 text-sm text-red-700">
              {error}
            </div>
          )}
          {/* Title */}
          <div>
            <label className="block text-sm font-display text-sand-700 tracking-wider mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="My Screenplay"
              className="w-full px-3 py-2 bg-white/70 border border-sand-600/25 rounded text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40"
            />
          </div>

          {/* Genre */}
          <div>
            <label className="block text-sm font-display text-sand-700 tracking-wider mb-1">
              Genre
            </label>
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="w-full px-3 py-2 bg-white/70 border border-sand-600/25 rounded text-stone-800 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40"
            >
              <option value="">Select genre...</option>
              {GENRES.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>

          {/* Time Period */}
          <div>
            <label className="block text-sm font-display text-sand-700 tracking-wider mb-1">
              Time Period
            </label>
            <input
              type="text"
              value={timePeriod}
              onChange={(e) => setTimePeriod(e.target.value)}
              placeholder="Modern, 1970s, Medieval..."
              className="w-full px-3 py-2 bg-white/70 border border-sand-600/25 rounded text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40"
            />
          </div>

          {/* Visual Tone */}
          <div>
            <label className="block text-sm font-display text-sand-700 tracking-wider mb-1">
              Visual Tone
            </label>
            <input
              type="text"
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              placeholder="Warm, nostalgic, gritty..."
              className="w-full px-3 py-2 bg-white/70 border border-sand-600/25 rounded text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40"
            />
          </div>

          {/* Reference Films */}
          <div>
            <label className="block text-sm font-display text-sand-700 tracking-wider mb-1">
              Reference Films
            </label>
            <input
              type="text"
              value={filmsInput}
              onChange={(e) => setFilmsInput(e.target.value)}
              placeholder="Blade Runner, No Country for Old Men..."
              className="w-full px-3 py-2 bg-white/70 border border-sand-600/25 rounded text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40"
            />
            <p className="text-xs text-stone-500 font-mono mt-1">Comma-separated</p>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={!title.trim() || submitting}
            className="w-full px-4 py-3 bg-sand-700 text-white border border-sand-600 rounded font-display tracking-wider text-lg hover:bg-sand-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Creating..." : "Create Project"}
          </button>
        </form>
      </main>
    </div>
  );
}
