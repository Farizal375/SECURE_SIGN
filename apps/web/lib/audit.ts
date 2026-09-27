import { createHash } from "crypto";

export function auditEventHash(
  eventType: string,
  eventData: Record<string, unknown>,
  previousEventHash: string,
): string {
  const payload = JSON.stringify({ eventType, ...eventData });
  return createHash("sha256")
    .update(payload + previousEventHash)
    .digest("hex");
}
