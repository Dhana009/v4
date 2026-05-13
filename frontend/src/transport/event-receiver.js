// transport/event-receiver.js — Backend event receiver and normalizer
// Cluster 5: Transport wiring

export function parseEvent(rawData) {
  if (!rawData) return null;

  let parsed = rawData;
  if (typeof rawData === "string") {
    try {
      parsed = JSON.parse(rawData);
    } catch {
      return null;
    }
  }

  if (!parsed || typeof parsed !== "object") return null;

  const type = parsed.type ?? parsed.event_type ?? null;
  if (!type) return null;

  const payload = parsed.payload ?? parsed.data ?? parsed;

  return {
    type,
    payload: typeof payload === "object" ? payload : {},
    raw: parsed,
  };
}

export function isKnownEventType(type, knownTypes) {
  if (!type || !knownTypes) return false;
  return Object.values(knownTypes).includes(type);
}
