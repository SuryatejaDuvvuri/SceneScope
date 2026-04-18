import { getToken } from "./auth";
import type {
  Project,
  ProjectSummary,
  ProjectCreateRequest,
  Scene,
  ScenesCreateRequest,
  RefineRequest,
  ConsultRequest,
  ConsultFollowUpRequest,
  ConsultResponse,
  StructureAnalysis,
  SceneAudio,
} from "./types";
import { BACKEND_URL } from "./urls";

const BASE_URL = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...options.headers },
    ...options,
  });

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem("scenescope_token");
      window.location.href = "/";
      throw new Error("Unauthorized");
    }
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }

  return res.json();
}

// ── Projects ──

export async function createProject(
  data: ProjectCreateRequest
): Promise<Project> {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>("/projects");
}

export async function getProject(id: string): Promise<Project> {
  return request<Project>(`/projects/${id}`);
}

export async function deleteProject(id: string): Promise<void> {
  return request(`/projects/${id}`, { method: "DELETE" });
}

// ── Scenes ──

export async function createScenes(
  projectId: string,
  data: ScenesCreateRequest
): Promise<Scene[]> {
  return request<Scene[]>(`/projects/${projectId}/scenes`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function resetScenes(projectId: string): Promise<void> {
  return request(`/projects/${projectId}/scenes`, { method: "DELETE" });
}

export async function refineScene(
  sceneId: string,
  data: RefineRequest
): Promise<Scene> {
  return request<Scene>(`/scenes/${sceneId}/refine`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function lockScene(sceneId: string): Promise<Scene> {
  return request<Scene>(`/scenes/${sceneId}/lock`, { method: "POST" });
}

export async function unlockScene(sceneId: string): Promise<Scene> {
  return request<Scene>(`/scenes/${sceneId}/unlock`, { method: "POST" });
}

// ── Director Consultation ──

export async function consultDirector(
  sceneId: string,
  data: ConsultRequest
): Promise<ConsultResponse> {
  return request<ConsultResponse>(`/scenes/${sceneId}/consult`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function respondToDirector(
  sceneId: string,
  data: ConsultFollowUpRequest
): Promise<ConsultResponse> {
  return request<ConsultResponse>(`/scenes/${sceneId}/consult/respond`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Structure Analysis ──

export async function getStructureAnalysis(
  projectId: string
): Promise<StructureAnalysis> {
  return request<StructureAnalysis>(`/projects/${projectId}/structure`);
}

// ── Audio ──

export async function generateSceneAudio(sceneId: string): Promise<SceneAudio> {
  return request<SceneAudio>(`/scenes/${sceneId}/audio`, { method: "POST" });
}

export async function getSceneAudio(sceneId: string): Promise<SceneAudio | null> {
  try {
    return await request<SceneAudio>(`/scenes/${sceneId}/audio`);
  } catch {
    return null;
  }
}

// ── Export ──

export async function exportStoryboard(projectId: string): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/export`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.blob();
}
