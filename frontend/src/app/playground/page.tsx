import type { Metadata } from "next";
import { Suspense } from "react";

import { BackendUnavailable } from "@/components/backend-unavailable";
import { listModels } from "@/lib/api";
import type { ModelInfo } from "@/lib/api-types";

import { Playground } from "./playground";

export const metadata: Metadata = {
  title: "Playground · ModelMesh AI",
};

async function PlaygroundLoader() {
  let models: ModelInfo[];
  try {
    models = await listModels();
  } catch {
    return <BackendUnavailable />;
  }

  if (models.length === 0) {
    return (
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        No models are configured. Set a provider in <code className="font-mono">backend/.env</code>{" "}
        or enable the mock provider.
      </p>
    );
  }

  return <Playground models={models} />;
}

export default function PlaygroundPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
          Playground
        </h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Chat with any model the gateway serves. Requests go through{" "}
          <code className="font-mono">POST /v1/chat/completions</code>.
        </p>
      </div>
      <Suspense fallback={<p className="text-sm text-zinc-500">Loading models…</p>}>
        <PlaygroundLoader />
      </Suspense>
    </main>
  );
}
