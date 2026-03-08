// ── Mood ──

export type Mood = "tense" | "uplifting" | "somber" | "action";

// ── Project ──

export interface Project {
  id: string;
  title: string;
  genre: string | null;
  time_period: string | null;
  tone: string | null;
  films: string[];
  scenes: Scene[];
  created_at: string;
  updated_at: string;
}

export interface ProjectSummary {
  id: string;
  title: string;
  genre: string | null;
  scene_count: number;
  created_at: string;
}

export interface ProjectCreateRequest {
  title: string;
  genre?: string;
  time_period?: string;
  tone?: string;
  films?: string[];
}

// ── Scene ──

export interface ClarifyingQuestion {
  question: string;
  suggestion: string;
}

export interface Scene {
  id: string;
  project_id: string;
  scene_number: number;
  heading: string | null;
  description: string;
  mood: Mood | null;
  mood_confidence: number | null;
  vague_elements: string[];
  clarifying_questions: ClarifyingQuestion[];
  visual_summary: string | null;
  shot_suggestions: ShotSuggestions | null;
  current_iteration: SceneIteration | null;
  iterations: SceneIteration[];
  locked: boolean;
  created_at: string;
  updated_at: string;
}

export interface DirectorNotes {
  interpretation: string;
  visual_direction: string;
  reasoning: string;
  prompt_modifier: string;
  follow_up: string | null;
}

export interface SceneIteration {
  id: string;
  iteration_number: number;
  prompt_used: string;
  answers: Record<string, string> | null;
  feedback: string | null;
  sketch_url: string | null;
  image_provider: string | null;
  director_notes: DirectorNotes | null;
  created_at: string;
}

// ── API Request/Response types ──

export interface ScenesCreateRequest {
  text: string;
}

export interface ScenesCreateResponse {
  scenes: Scene[];
}

export interface RefineRequest {
  answers: Record<string, string>;
  feedback?: string;
  director_notes?: DirectorNotes;
}

export interface ConsultRequest {
  feedback: string;
  answers: Record<string, string>;
}

export interface ConsultFollowUpRequest {
  response: string;
  conversation_history: Array<{
    director: DirectorNotes;
    user_response: string;
  }>;
}

export interface ConsultResponse {
  interpretation: string;
  visual_direction: string;
  reasoning: string;
  prompt_modifier: string;
  follow_up: string | null;
}

// ── Shot Suggestions ──

export interface ShotSuggestion {
  shot_type: string;
  angle: string;
  movement: string;
  reasoning: string;
}

export interface ShotSuggestions {
  primary: ShotSuggestion;
  alternatives: ShotSuggestion[];
}

// ── Structure Analysis ──

export interface TonalShift {
  from_scene: number;
  to_scene: number;
  from_mood: string;
  to_mood: string;
  magnitude: number;
}

export interface StructureAnalysis {
  scene_moods: Array<{
    scene_number: number;
    heading: string | null;
    mood: string | null;
    confidence: number | null;
  }>;
  tonal_shifts: TonalShift[];
  pacing: string;
  arc_summary: string;
}
