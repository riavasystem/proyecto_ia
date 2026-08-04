"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";

interface Conversation {
  id: string;
  channel: string;
  status: string;
  created_at: string;
}

interface Message {
  id: string;
  role: string;
  content: string;
  intent: string | null;
  created_at: string;
}

interface ConversationDetail extends Conversation {
  messages: Message[];
}

export default function ConversacionesPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<ConversationDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Conversation[]>("/api/v1/admin/conversations")
      .then(setConversations)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar"))
      .finally(() => setIsLoading(false));
  }, []);

  async function openConversation(id: string) {
    try {
      setSelected(await apiFetch<ConversationDetail>(`/api/v1/admin/conversations/${id}`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la conversación");
    }
  }

  return (
    <main className="flex gap-6 p-8">
      <div className="flex w-80 shrink-0 flex-col gap-3">
        <h1 className="text-xl font-semibold tracking-tight">Conversaciones</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {isLoading ? (
          <p className="text-sm text-zinc-500">Cargando…</p>
        ) : conversations.length === 0 ? (
          <p className="text-sm text-zinc-500">Todavía no hay conversaciones.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {conversations.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => openConversation(c.id)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                    selected?.id === c.id
                      ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                      : "hover:bg-zinc-100 dark:hover:bg-zinc-900"
                  }`}
                >
                  <span className="block font-medium">{c.channel}</span>
                  <span className="block text-xs opacity-70">
                    {c.status} · {new Date(c.created_at).toLocaleString("es-CL")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex-1 border-l border-zinc-200 pl-6 dark:border-zinc-800">
        {selected ? (
          <div className="flex flex-col gap-3">
            {selected.messages.map((m) => (
              <div
                key={m.id}
                className={`max-w-lg rounded-lg px-3 py-2 text-sm ${
                  m.role === "assistant"
                    ? "bg-zinc-100 dark:bg-zinc-900"
                    : "self-end bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                }`}
              >
                <p>{m.content}</p>
                {m.intent && <p className="mt-1 text-xs opacity-60">intent: {m.intent}</p>}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-zinc-500">Seleccioná una conversación para ver el historial.</p>
        )}
      </div>
    </main>
  );
}
