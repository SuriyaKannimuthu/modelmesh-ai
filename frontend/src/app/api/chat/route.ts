import { API_URL } from "@/lib/api";

/**
 * Forwards chat requests from the browser to the backend gateway.
 *
 * Keeps the backend address (and, later, the console's gateway credentials) on the server,
 * and avoids cross-origin requests from the browser.
 */
export async function POST(request: Request) {
  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/v1/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { error: { type: "backend_unreachable", message: "Could not reach the ModelMesh backend." } },
      { status: 502 },
    );
  }

  const headers = new Headers({
    "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
  });
  const retryAfter = upstream.headers.get("Retry-After");
  if (retryAfter) headers.set("Retry-After", retryAfter);

  return new Response(upstream.body, { status: upstream.status, headers });
}
