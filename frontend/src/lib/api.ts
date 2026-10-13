// Server-side client for the ModelMesh backend. The browser never calls the backend directly;
// it goes through Route Handlers under `src/app/api/`.

import { readJson, type HealthResponse, type ModelInfo } from "@/lib/api-types";

export const API_URL = process.env.MODELMESH_API_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse | null> {
  try {
    return await readJson<HealthResponse>(
      await fetch(`${API_URL}/v1/health`, { cache: "no-store" }),
    );
  } catch {
    return null;
  }
}

export async function listModels(): Promise<ModelInfo[]> {
  const res = await fetch(`${API_URL}/v1/models`, { cache: "no-store" });
  return (await readJson<{ data: ModelInfo[] }>(res)).data;
}
