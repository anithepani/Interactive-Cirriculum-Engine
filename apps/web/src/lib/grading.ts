import { ReviewPayload, TraceStateRow } from "./types";

export function gradeOutputPrediction(expected: string, actual: string): boolean {
  return expected.trim() === actual.trim();
}

export function gradeFillGap(expected: string, actual: string): boolean {
  // Strip all whitespaces
  const cleanExpected = expected.replace(/\s+/g, "");
  const cleanActual = actual.replace(/\s+/g, "");
  return cleanExpected === cleanActual;
}

export function gradeSpotBug(expectedLine: number, actualLine: number): boolean {
  return expectedLine === actualLine;
}

export function gradeConceptRecall(expectedIndex: number, actualIndex: number): boolean {
  return expectedIndex === actualIndex;
}

export function gradeTraceState(expectedTable: TraceStateRow[], actualTable: TraceStateRow[]): boolean {
  if (expectedTable.length !== actualTable.length) return false;
  
  for (let i = 0; i < expectedTable.length; i++) {
    const expectedRow = expectedTable[i];
    const actualRow = actualTable[i];
    
    if (String(expectedRow.iteration) !== String(actualRow.iteration)) return false;
    
    const expectedVars = expectedRow.variables;
    const actualVars = actualRow.variables;
    
    const expectedKeys = Object.keys(expectedVars);
    if (expectedKeys.length !== Object.keys(actualVars).length) return false;
    
    for (const key of expectedKeys) {
      if (String(expectedVars[key]).trim() !== String(actualVars[key]).trim()) return false;
    }
  }
  return true;
}

export function gradeLegacy(expected: string, actual: string): boolean {
  // Simple heuristic or always just rely on user self-grading for legacy flashcards.
  // We'll return true if actual is not empty, for a simple check, or just self-grade.
  return actual.trim().length > 0;
}
