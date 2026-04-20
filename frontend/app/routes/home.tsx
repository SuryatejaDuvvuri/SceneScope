import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import type { Route } from "./+types/home";
import type { ProjectSummary } from "~/lib/types";
import { deleteProject, listProjects } from "~/lib/api";
import { useAuth } from "~/lib/auth";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "SceneScope — See Your Screenplay Before You Shoot It" },
    { name: "description", content: "AI based screenplay pre-visualization. Analyze scenes, generate storyboards, and refine your vision through intelligent director collaboration." },
  ];
}

export default function Home() {
  const navigate = useNavigate();
  const { user, loading: authLoading, login, logout } = useAuth();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const hasProject = projects.length > 0;

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    listProjects()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user]);

  async function handleDeleteProject(projectId: string, title: string) {
    const confirmed = window.confirm(`Delete \"${title}\"? This will remove all scenes and iterations for the project.`);
    if (!confirmed) return;

    try {
      setDeletingId(projectId);
      await deleteProject(projectId);
      setProjects((current) => current.filter((project) => project.id !== projectId));
    } catch (error) {
      console.error("Failed to delete project:", error);
      window.alert("Failed to delete project. Please try again.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-space-950 overflow-x-hidden">
      <nav className="fixed top-0 left-0 right-0 z-50 bg-space-950/80 backdrop-blur-sm border-b border-sand-600/10">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-display text-xl text-sand-800">SceneScope</span>
          {user ? (
            <div className="flex items-center gap-3">
              {user.avatar_url && (
                <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full border border-sand-600/30" referrerPolicy="no-referrer" />
              )}
              <span className="text-sm text-stone-600 hidden sm:inline">{user.name || user.email}</span>
              <button onClick={logout} className="text-xs text-stone-500 hover:text-stone-700 font-mono transition-colors">
                Sign Out
              </button>
            </div>
          ) : (
            <button onClick={login} className="px-4 py-1.5 text-sm text-sand-800 border border-sand-600/40 rounded hover:bg-sand-600/10 transition-all font-display">
              Sign In
            </button>
          )}
        </div>
      </nav>
      <section className="relative min-h-screen flex flex-col items-center justify-center px-6">
        {/* Warm radial glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(212,144,34,0.12)_0%,_transparent_60%)]" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-sand-400/[0.08] rounded-full blur-[200px]" />

        {/* Title */}
        <div className="relative z-10 text-center poof">
          <h1 className="font-display text-[5rem] sm:text-[7rem] md:text-[9rem] leading-[0.85] text-sand-800 neon-text">
            Scene
            <br />
            <span className="text-sand-700">Scope</span>
          </h1>
        </div>

        <p className="relative z-10 mt-8 text-xl sm:text-2xl text-stone-700 text-center max-w-2xl leading-relaxed">
          See your screenplay <span className="text-sand-700 font-semibold">before</span> you shoot it.
        </p>
        <p className="relative z-10 mt-3 text-base text-stone-500 text-center max-w-lg">
          AI based pre-visualization tool that understands mood, tone, and dramatic intent.
        </p>

        <div className="relative z-10 mt-12 flex flex-col sm:flex-row items-center gap-4">
          {user ? (
            <button
              onClick={() => navigate("/projects/new")}
              className="px-10 py-4 bg-sand-700 text-white border-2 border-sand-600 rounded font-display text-xl hover:bg-sand-800 hover:scale-[1.03] transition-all duration-300 shadow-lg shadow-sand-700/25"
            >
              Start Creating
            </button>
          ) : (
            <button
              onClick={login}
              className="px-10 py-4 bg-sand-700 text-white border-2 border-sand-600 rounded font-display text-xl hover:bg-sand-800 hover:scale-[1.03] transition-all duration-300 shadow-lg shadow-sand-700/25 flex items-center gap-3"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              Sign in with Google
            </button>
          )}
          <button
            onClick={() => document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })}
            className="px-10 py-4 text-sand-800 border-2 border-sand-600/40 rounded font-display text-xl hover:bg-sand-600/10 hover:border-sand-600/60 transition-all duration-300"
          >
            How It Works
          </button>
        </div>

        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-40">
          <span className="text-xs text-stone-500 font-mono tracking-widest">SCROLL</span>
          <div className="w-px h-8 bg-gradient-to-b from-sand-600/50 to-transparent" />
        </div>
      </section>

      <section className="py-14">
        <div className="max-w-5xl mx-auto px-6">
          <div className="rounded-xl border border-sand-600/25 bg-white/45 p-7">
            <h3 className="font-display text-2xl text-sand-800 mb-4">Pilot Usage & Expectations</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
              {[
                "1 project per user",
                "1-3 scenes per upload",
                "1-3 scenes per project",
                "120 image generations/day",
                "3 refinements max per scene",
                "Avoid spamming generate actions",
              ].map((item) => (
                <div key={item} className="flex items-start gap-2 rounded-md bg-white/65 border border-sand-600/20 px-3 py-2">
                  <span className="text-sand-700 mt-0.5">•</span>
                  <span className="text-sm text-stone-700 font-mono">{item}</span>
                </div>
              ))}
            </div>
            <p className="text-sm text-stone-600 leading-relaxed">
              This is a pilot release. Generated storyboard images and dialogue audio are creative aids, not final production output.
              If tone is off, refine with clearer scene details and feedback.
            </p>
            <p className="text-sm text-stone-600 leading-relaxed mt-2">
              Free-tier hosting may pause or reset after inactivity. Export any important storyboard work promptly.
            </p>
          </div>
        </div>
      </section>

      <section className="relative py-32">
        <div className="absolute inset-0 bg-gradient-to-b from-space-950 via-space-900 to-space-950" />
        <div className="relative z-10 max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="p-8 rounded-lg border border-sand-600/25 bg-white/40 backdrop-blur-sm swish">
              <div className="font-mono text-xs text-sand-700 mb-6 tracking-[0.2em]">FROM SCRIPT</div>
              <div className="font-mono text-base text-stone-700 leading-loose space-y-4">
                <p className="text-sand-800 font-bold text-lg">INT. ABANDONED WAREHOUSE — NIGHT</p>
                <p className="text-stone-600">Rain hammers against broken skylights. A single bulb swings on a wire, carving the dark into shards of amber and black.</p>
                <p className="text-stone-500 italic">DETECTIVE COLE steps through the doorway, badge catching the light.</p>
              </div>
            </div>

            <div className="space-y-8">
              <h2 className="font-display text-4xl sm:text-5xl text-sand-800 leading-tight">
                The gap between
                <br />
                script & screen
              </h2>
              <p className="text-lg text-stone-600 leading-relaxed">
                A screenplay is a blueprint. When a director <span className="text-sand-800 font-medium">sees</span> what
                they read it is unique, personal and until now, trapped inside their head.
              </p>
              <p className="text-lg text-stone-600 leading-relaxed">
                SceneScope translates words into storyboard sketches that capture <span className="text-sand-800 font-medium">feeling</span>, not just content.
              </p>
            </div>
          </div>
        </div>
      </section>
      <section id="how-it-works" className="py-32 relative">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="font-display text-5xl text-center text-sand-800 mb-4">
            How It Works
          </h2>
          <p className="text-center text-stone-500 mb-20 text-lg">Four steps. Script to storyboard.</p>
          <div className="hidden lg:block absolute left-1/2 -translate-x-1/2 top-[calc(50%+40px)] w-[70%] h-px bg-gradient-to-r from-transparent via-sand-500/40 to-transparent" />

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { num: "01", title: "Paste", desc: "Drop in your screenplay! Fountain or plain text. SceneScope reads it like a director would.", icon: "📝" },
              { num: "02", title: "Analyze", desc: "AI breaks scenes apart: mood, tone, visual elements, shot suggestions, and what's left unsaid.", icon: "🔍" },
              { num: "03", title: "Refine", desc: "Answer smart questions, give feedback, watch the storyboard evolve through iterative dialogue.", icon: "🎯" },
              { num: "04", title: "Export", desc: "Lock scenes and export a complete visual storyboard for your team, pitch, or reference.", icon: "🎬" },
            ].map(({ num, title, desc, icon }) => (
              <div key={num} className="relative p-6 rounded-lg border border-sand-600/20 bg-white/30 hover:bg-white/50 hover:border-sand-500/35 transition-all group sparkle-particles">
                <div className="text-4xl mb-4">{icon}</div>
                <div className="font-display text-5xl text-sand-400/20 absolute top-4 right-4">{num}</div>
                <h3 className="font-display text-xl text-sand-800 mb-2">{title}</h3>
                <p className="text-sm text-stone-600 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-32 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-space-950 via-space-900/60 to-space-950" />
        <div className="relative z-10 max-w-5xl mx-auto px-6">
          <h2 className="font-display text-5xl text-center text-sand-800 mb-20">
            What's Under The Hood
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-10">
            {[
              {
                title: "Mood Classification",
                desc: "Detects emotional tone like tense, somber, uplifting, and action so your storyboard not just looks right but feels right.",
                icon: "🎭",
              },
              {
                title: "Director Agent",
                desc: "An AI collaborator that interprets feedback, suggests compositions, and refines the visual prompt like a pre-production conversation.",
                icon: "🎥",
              },
              {
                title: "Visual Consistency",
                desc: "Scene-to-scene coherence across iterations. When you refine, the core visual identity carries forward.",
                icon: "🧩",
              },
              {
                title: "Smart Questions",
                desc: "Dynamic clarifying questions that evolve with each iteration to push towards specificity.",
                icon: "💡",
              },
            ].map(({ title, desc, icon }) => (
              <div key={title} className="flex gap-5 p-6 rounded-lg border border-sand-600/15 bg-white/30 hover:bg-white/50 hover:border-sand-500/30 transition-all">
                <div className="text-3xl flex-shrink-0 mt-1">{icon}</div>
                <div>
                  <h3 className="font-display text-lg text-sand-800 mb-2">{title}</h3>
                  <p className="text-base text-stone-600 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-24 relative">
        <div className="max-w-3xl mx-auto px-6 text-center poof">
          <blockquote className="relative z-10">
            <p className="text-2xl sm:text-3xl text-stone-700 italic leading-relaxed font-light">
              "Every great film starts with <span className="text-sand-800 not-italic font-semibold">seeing it</span> in your mind's eye."
            </p>
            <footer className="mt-6 text-sm text-stone-500 font-mono">
              SceneScope helps you show it to everyone else.
            </footer>
          </blockquote>
        </div>
      </section>

      <section id="projects" className="py-24">
        <div className="max-w-5xl mx-auto px-6">
          {!user ? (
            <div className="text-center py-24 rounded-lg border border-sand-600/20 bg-white/30">
              <div className="text-5xl mb-5">🔐</div>
              <p className="text-stone-700 mb-2 text-xl">Sign in to see your projects</p>
              <p className="text-stone-500 text-base mb-8">Each user gets their own private workspace.</p>
              <button
                onClick={login}
                className="px-8 py-3 bg-sand-700 text-white border-2 border-sand-600 rounded font-display text-lg hover:bg-sand-800 transition-all shadow-md flex items-center gap-3 mx-auto"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                Sign in with Google
              </button>
            </div>
          ) : (
          <>
          <div className="flex items-center justify-between mb-10">
            <h2 className="font-display text-3xl text-sand-800">Your Projects</h2>
            <button
              onClick={() => navigate("/projects/new")}
              disabled={hasProject}
              className="px-5 py-2.5 bg-sand-700 text-white border border-sand-600 rounded text-sm font-display hover:bg-sand-800 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-sand-700"
            >
              {hasProject ? "Pilot: 1 Project Max" : "New Project"}
            </button>
          </div>

          {loading ? (
            <div className="py-16 flex justify-center">
              <div className="holo-spinner" />
            </div>
          ) : projects.length === 0 ? (
            <div className="text-center py-24 rounded-lg border border-sand-600/20 bg-white/30">
              <div className="text-5xl mb-5">🎬</div>
              <p className="text-stone-700 mb-2 text-xl">No projects yet</p>
              <p className="text-stone-500 text-base mb-8">Paste a screenplay and watch it come to life.</p>
              <button
                onClick={() => navigate("/projects/new")}
                className="px-8 py-3 bg-sand-700 text-white border-2 border-sand-600 rounded font-display text-lg hover:bg-sand-800 transition-all shadow-md"
              >
                Create Your First Project
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="p-6 bg-white/30 border border-sand-600/15 rounded-lg hover:border-sand-500/40 hover:bg-white/50 transition-all group shadow-sm"
                >
                  <div className="flex items-start justify-between gap-3">
                    <button
                      onClick={() => navigate(`/projects/${project.id}`)}
                      className="text-left flex-1 min-w-0"
                    >
                      <h3 className="font-display text-lg text-sand-800 group-hover:text-sand-900">{project.title}</h3>
                      {project.genre && (
                        <p className="text-sm text-stone-500 mt-1">{project.genre}</p>
                      )}
                      <p className="text-sm text-stone-400 mt-4 font-mono">
                        {project.scene_count} scene{project.scene_count !== 1 ? "s" : ""}
                      </p>
                    </button>
                    <button
                      onClick={() => handleDeleteProject(project.id, project.title)}
                      disabled={deletingId === project.id}
                      className="flex-shrink-0 px-2.5 py-1.5 text-xs text-red-700 border border-red-300/70 rounded hover:bg-red-50/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label={`Delete ${project.title}`}
                    >
                      {deletingId === project.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          </>
          )}
        </div>
      </section>

      <footer className="border-t border-sand-600/15 py-8">
        <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="font-display text-sm text-sand-700">SceneScope</span>
          <span className="text-xs text-stone-500 font-mono"></span>
        </div>
      </footer>
    </div>
  );
}
