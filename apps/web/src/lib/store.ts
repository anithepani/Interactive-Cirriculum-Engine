import { create } from "zustand";

interface PlayerState {
  currentCheckpointIndex: number;
  answers: Record<string, string>;
  isExerciseOpen: boolean;
  setCurrentCheckpointIndex: (index: number) => void;
  setAnswer: (checkpointId: string, answer: string) => void;
  openExercise: () => void;
  closeExercise: () => void;
  reset: () => void;
}

export const usePlayerStore = create<PlayerState>((set) => ({
  currentCheckpointIndex: 0,
  answers: {},
  isExerciseOpen: false,
  setCurrentCheckpointIndex: (index) => set({ currentCheckpointIndex: index }),
  setAnswer: (checkpointId, answer) =>
    set((state) => ({ answers: { ...state.answers, [checkpointId]: answer } })),
  openExercise: () => set({ isExerciseOpen: true }),
  closeExercise: () => set({ isExerciseOpen: false }),
  reset: () => set({ currentCheckpointIndex: 0, answers: {}, isExerciseOpen: false }),
}));
