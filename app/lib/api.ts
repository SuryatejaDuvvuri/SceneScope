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
  VoiceInfo,
} from "./types";
import { API_ROOT } from "./publicUrl";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_ROOT}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
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

// ── Export ──

export async function exportStoryboard(projectId: string): Promise<Blob> {
  const res = await fetch(`${API_ROOT}/projects/${projectId}/export`);
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.blob();
}

// ── Audio ──

export async function generateSceneAudio(sceneId: string): Promise<SceneAudio> {
  return request<SceneAudio>(`/scenes/${sceneId}/audio`, { method: "POST" });
}

export async function getSceneAudio(sceneId: string): Promise<SceneAudio | null> {
  return request<SceneAudio | null>(`/scenes/${sceneId}/audio`);
}

export async function getProjectVoices(projectId: string): Promise<VoiceInfo[]> {
  return request<VoiceInfo[]>(`/projects/${projectId}/voices`);
}

export async function setProjectVoice(
  projectId: string,
  characterName: string,
  voiceId: string
): Promise<VoiceInfo> {
  return request<VoiceInfo>(`/projects/${projectId}/voices/${encodeURIComponent(characterName)}`, {
    method: "PUT",
    body: JSON.stringify({ voice_id: voiceId }),
  });
}
