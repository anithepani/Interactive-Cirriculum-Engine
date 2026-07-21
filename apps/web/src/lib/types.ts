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
  // Persisted attempt state (hydrated from the backend on load) so markers +
  // locked review survive reloads.
  status?: "correct" | "incorrect" | null;
  submitted_answer?: string | null;
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

// Live learner statistics (Block D) — served by /api/v1/stats/*. Replaces the
// old hardcoded frontend heuristics (count*3 exercises, count*1.5 hours).
export interface StatsCategory {
  category: string;
  count: number;
  percent: number;
}

export interface StatsOverview {
  total_curricula: number;
  ready_curricula: number;
  completed_exercises: number;
  correct_exercises: number;
  accuracy: number;
  hours_learned: number;
  watched_seconds: number;
  categories?: StatsCategory[];
}

export interface ExercisePayload {
  type?: string;
  question?: string;
  prompt?: string;
  // Supporting code snippet / problem context shown alongside the prompt
  // (extracted from the instructor's screen via OCR, when available).
  context?: string;
  options?: string[];
  answer_index?: number;
  answer_idx?: number;
  reference_answer?: string;
  starter_code?: string;
  starter?: string;
  solution?: string;
  // Coding exercises: the reference solution (used for the diff-style review).
  reference_solution?: string;
  language?: string;
  min_similarity?: number;
  // Debug exercises: the buggy snippet the learner must fix (seeds the editor).
  buggy_code?: string;
  // Debug exercises: the corrected code (reference answer shown in review).
  fixed_code?: string;
  tests?: string[];
  // Coding exercises: visible tests appended on "Run" to stream real feedback
  // (hidden tests stay hidden until Submit).
  tests_visible?: string[];
  bug_explanation?: string;
}

// Result surfaced back to the modal after a Submit (/evaluate) call. Includes
// execution output so the modal's output window can display stdout/stderr.
export interface ExerciseSubmitResult {
  passed: boolean;
  message?: string;
  stdout?: string;
  stderr?: string;
}

// Result of a Run (/execute) call — trial execution without hidden tests.
export interface ExerciseRunResult {
  passed: boolean;
  stdout?: string;
  stderr?: string;
  message?: string;
}
