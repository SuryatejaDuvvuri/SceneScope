import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import type { Route } from "./+types/home";
import type { ProjectSummary } from "~/lib/types";
import { listProjects } from "~/lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "SceneScope" },
    { name: "description", content: "AI-powered screenplay pre-visualization" },
  ];
}

export default function Home() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* ── Header ── */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">SceneScope</h1>
          <p className="mt-2 text-gray-500 dark:text-gray-400">
            See what your screenplay actually looks like.
          </p>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Projects</h2>
          <button
            onClick={() => navigate("/projects/new")}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            New Project
          </button>
        </div>

        {loading ? (
          <div className="text-gray-400 dark:text-gray-500 py-12 text-center">Loading...</div>
        ) : projects.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-xl">
            <p className="text-gray-500 dark:text-gray-400 mb-4">No projects yet</p>
            <button
              onClick={() => navigate("/projects/new")}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Create your first project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="text-left p-5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
              >
                <h3 className="font-semibold text-gray-900 dark:text-white">{project.title}</h3>
                {project.genre && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{project.genre}</p>
                )}
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
                  {project.scene_count} scene{project.scene_count !== 1 ? "s" : ""}
                </p>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
