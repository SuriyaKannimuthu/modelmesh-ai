"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import {
  readJson,
  type ChatCompletionRequest,
  type ChatCompletionResponse,
  type ChatMessage,
  type ModelInfo,
} from "@/lib/api-types";

type TurnMeta = Pick<ChatCompletionResponse, "model" | "provider" | "usage" | "latency_ms"> & {
  finishReason: string;
};

type Turn = {
  role: "user" | "assistant";
  content: string;
  meta?: TurnMeta;
};

const inputClass =
  "w-full rounded-lg border border-black/[.12] bg-white px-3 py-2 text-sm text-black outline-none focus:border-black/40 dark:border-white/[.18] dark:bg-zinc-900 dark:text-zinc-50 dark:focus:border-white/40";

const labelClass = "mb-1 block text-xs font-medium uppercase tracking-wide text-zinc-500";

async function createChatCompletion(body: ChatCompletionRequest) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJson<ChatCompletionResponse>(res);
}

function parseOptionalNumber(value: string): number | undefined {
  if (value.trim() === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function Playground({ models }: { models: ModelInfo[] }) {
  const [model, setModel] = useState(models[0].id);
  const [system, setSystem] = useState("");
  const [maxTokens, setMaxTokens] = useState("");
  const [temperature, setTemperature] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns, pending]);

  async function send() {
    const text = input.trim();
    if (!text || pending) return;

    const history: Turn[] = [...turns, { role: "user", content: text }];
    const messages: ChatMessage[] = history.map(({ role, content }) => ({ role, content }));
    if (system.trim()) messages.unshift({ role: "system", content: system.trim() });

    setTurns(history);
    setInput("");
    setError(null);
    setPending(true);

    try {
      const response = await createChatCompletion({
        model,
        messages,
        max_tokens: parseOptionalNumber(maxTokens),
        temperature: parseOptionalNumber(temperature),
      });
      const choice = response.choices[0];
      setTurns([
        ...history,
        {
          role: "assistant",
          content: choice.message.content,
          meta: {
            model: response.model,
            provider: response.provider,
            usage: response.usage,
            latency_ms: response.latency_ms,
            finishReason: choice.finish_reason,
          },
        },
      ]);
    } catch (err) {
      // Roll back the unanswered user turn so the conversation stays valid to resend.
      setTurns(turns);
      setInput(text);
      setError(
        err instanceof TypeError
          ? "Could not reach the server."
          : err instanceof Error
            ? err.message
            : "Request failed.",
      );
    } finally {
      setPending(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <div className="grid flex-1 gap-6 lg:grid-cols-[280px_1fr]">
      <aside className="flex flex-col gap-4">
        <div>
          <label htmlFor="model" className={labelClass}>
            Model
          </label>
          <select
            id="model"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className={inputClass}
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.id}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="system" className={labelClass}>
            System prompt
          </label>
          <textarea
            id="system"
            rows={4}
            value={system}
            onChange={(e) => setSystem(e.target.value)}
            placeholder="Optional instructions for the model"
            className={inputClass}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="max-tokens" className={labelClass}>
              Max tokens
            </label>
            <input
              id="max-tokens"
              type="number"
              min={1}
              value={maxTokens}
              onChange={(e) => setMaxTokens(e.target.value)}
              placeholder="Default"
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="temperature" className={labelClass}>
              Temperature
            </label>
            <input
              id="temperature"
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
              placeholder="Default"
              className={inputClass}
            />
          </div>
        </div>
        <p className="text-xs text-zinc-500">
          Leave blank for model defaults. Claude models don&apos;t accept a temperature.
        </p>

        <button
          type="button"
          onClick={() => {
            setTurns([]);
            setError(null);
          }}
          disabled={turns.length === 0 || pending}
          className="self-start text-sm text-zinc-500 hover:text-black disabled:opacity-40 dark:hover:text-zinc-50"
        >
          Clear conversation
        </button>
      </aside>

      <section className="flex min-h-[28rem] flex-col rounded-xl border border-black/[.08] bg-white dark:border-white/[.145] dark:bg-zinc-950">
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4 sm:p-6">
          {turns.length === 0 && !pending && (
            <p className="m-auto text-sm text-zinc-500">Send a message to start.</p>
          )}
          {turns.map((turn, index) => (
            <TurnView key={index} turn={turn} />
          ))}
          {pending && <p className="text-sm text-zinc-500">Waiting for {model}…</p>}
          <div ref={bottomRef} />
        </div>

        {error && (
          <p role="alert" className="border-t border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </p>
        )}

        <form
          onSubmit={onSubmit}
          className="flex gap-2 border-t border-black/[.08] p-3 dark:border-white/[.145]"
        >
          <textarea
            aria-label="Message"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Message (Enter to send, Shift+Enter for a new line)"
            className={`${inputClass} resize-none`}
          />
          <button
            type="submit"
            disabled={pending || !input.trim()}
            className="rounded-lg bg-black px-4 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-50 dark:text-black"
          >
            Send
          </button>
        </form>
      </section>
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";

  return (
    <div className={`flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm leading-6 ${
          isUser
            ? "bg-black text-white dark:bg-zinc-50 dark:text-black"
            : "bg-zinc-100 text-black dark:bg-zinc-900 dark:text-zinc-50"
        }`}
      >
        {turn.content || <span className="italic text-zinc-500">(empty response)</span>}
      </div>
      {turn.meta && (
        <p className="font-mono text-xs text-zinc-500">
          {turn.meta.model} · {turn.meta.usage.prompt_tokens} in / {turn.meta.usage.completion_tokens}{" "}
          out · {turn.meta.latency_ms} ms
          {turn.meta.finishReason !== "stop" && (
            <span className="ml-1 text-amber-600"> · {turn.meta.finishReason}</span>
          )}
        </p>
      )}
    </div>
  );
}
