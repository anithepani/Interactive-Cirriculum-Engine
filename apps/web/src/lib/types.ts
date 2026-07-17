export interface Segment {
  id: number;
  title: string;
  summary: string;
  start: number;
  end: number;
}

export interface Concept {
  id: string;
  label: string;
  description: string;
  difficulty: number;
}

export interface Checkpoint {
  id: number | string;
  curriculum_id?: number;
  segment_id: number;
  concept_id: string;
  ts: number;
  exercise_type: string;
  difficulty: number;
  exercise?: ExercisePayload | null;
}

export interface CurriculumDetail {
  id: number;
  title: string;
  video_url?: string;
  video_ref?: string;
  status: string;
  recap_status?: "none" | "processing" | "ready" | "failed";
  recap_url?: string | null;
  recap_transcript_html?: string | null;
  created_at?: string;
  ready_at?: string;
  segments: Segment[];
  concepts: Concept[];
  checkpoints: Checkpoint[];
}

export interface CurriculumSummary {
  id: number;
  title: string;
  status: string;
  created_at?: string;
  ready_at?: string;
  progress?: number;
}

export interface ExercisePayload {
  type?: string;
  question?: string;
  prompt?: string;
  options?: string[];
  answer_index?: number;
  answer_idx?: number;
  reference_answer?: string;
  starter_code?: string;
  starter?: string;
  solution?: string;
  language?: string;
  min_similarity?: number;
}
