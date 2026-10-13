import Link from "next/link";
import { Suspense } from "react";

import { BackendUnavailable } from "@/components/backend-unavailable";
import { getHealth } from "@/lib/api";

async function GatewayStatus() {
  const health = await getHealth();

  if (!health) {
    return (
      <div className="mt-4">
        <BackendUnavailable />
      </div>
    );
  }

  return (
    <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm sm:grid-cols-4">
      <dt className="text-zinc-500">Status</dt>
      <dd className="font-medium text-emerald-600 sm:col-span-3">{health.status}</dd>
      <dt className="text-zinc-500">Version</dt>
      <dd className="font-mono sm:col-span-3">{health.version}</dd>
      <dt className="text-zinc-500">Environment</dt>
      <dd className="font-mono sm:col-span-3">{health.environment}</dd>
    </dl>
  );
}

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-10 px-4 py-20 sm:px-6">
      <div className="flex flex-col gap-4">
        <h1 className="text-4xl font-semibold tracking-tight text-black dark:text-zinc-50">
          ModelMesh AI
        </h1>
        <p className="max-w-xl text-lg leading-8 text-zinc-600 dark:text-zinc-400">
          Enterprise LLM gateway for model routing, cost control, reliability, observability, and
          evaluation across providers.
        </p>
      </div>

      <section className="rounded-xl border border-black/[.08] bg-white p-6 dark:border-white/[.145] dark:bg-zinc-950">
        <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
          Gateway status
        </h2>
        <Suspense fallback={<p className="mt-4 text-sm text-zinc-500">Checking backend…</p>}>
          <GatewayStatus />
        </Suspense>
      </section>

      <Link
        href="/playground"
        className="group rounded-xl border border-black/[.08] bg-white p-6 transition-colors hover:border-black/20 dark:border-white/[.145] dark:bg-zinc-950 dark:hover:border-white/30"
      >
        <h2 className="font-medium text-black dark:text-zinc-50">
          Playground <span className="inline-block transition-transform group-hover:translate-x-0.5">→</span>
        </h2>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Send prompts through the gateway to any configured model and inspect tokens and latency.
        </p>
      </Link>
    </main>
  );
}
