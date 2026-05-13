// commands/validation.js — Frontend command validation (stub)
// Full implementation: S7-0508 (Stale/missing id and disabled command blocking)

/**
 * @stub S7-0306
 */
export const VALIDATION_STUB = true;

export function isValidCommandType(commandType) {
  return typeof commandType === "string" && commandType.trim().length > 0;
}
