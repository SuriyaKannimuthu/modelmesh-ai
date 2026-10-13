import { API_URL } from "@/lib/api";

export function BackendUnavailable() {
  return (
    <p className="text-sm text-red-600">
      Backend unreachable at <code className="font-mono">{API_URL}</code>. Start it with{" "}
      <code className="font-mono">uvicorn app.main:app --reload</code> in{" "}
      <code className="font-mono">backend/</code>.
    </p>
  );
}
