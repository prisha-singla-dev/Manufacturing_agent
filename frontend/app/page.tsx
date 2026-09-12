"use client";

import { useEffect, useState, useRef } from "react";
import { sendMessage, ChatResponse } from "@/lib/api";
import TableRenderer from "@/components/TableRenderer";
import ChartRenderer from "@/components/ChartRenderer";
import ConfirmWrite from "@/components/ConfirmWrite";

const PERSONAS = [
  { value: "inventory_manager", label: "Inventory Manager" },
  { value: "procurement_manager", label: "Procurement Manager" },
  { value: "owner", label: "Business Owner" },
];

type Message = { role: "user" | "assistant"; content: string; data?: ChatResponse };

export default function Page() {
  const [persona, setPersona] = useState(PERSONAS[0].value);
  const [threadId, setThreadId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // One thread per persona so switching roles doesn't mix conversation
  // history the LangGraph checkpointer keeps per thread_id.
  useEffect(() => {
    const key = `thread_${persona}`;
    let id = localStorage.getItem(key);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(key, id);
    }
    setThreadId(id);
    setMessages([]);
  }, [persona]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const data = await sendMessage(userMsg.content, persona, threadId);
      setMessages((m) => [...m, { role: "assistant", content: data.text, data }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-3xl mx-auto h-screen flex flex-col p-4">
      <header className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold">Manufacturing Agent</h1>
        <select
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        >
          {PERSONAS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        <button
          onClick={() => {
            const newId = crypto.randomUUID();
            localStorage.setItem(`thread_${persona}`, newId);
            setThreadId(newId);
            setMessages([]);
          }}
          className="text-xs text-gray-500 border rounded px-2 py-1 hover:bg-gray-100"
          title="Start a fresh thread if a conversation gets stuck"
        >
          New chat
        </button>
      </header>

      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400">Ask a question as the {PERSONAS.find(p => p.value === persona)?.label}.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div
              className={
                "inline-block max-w-full rounded-2xl px-4 py-2 text-sm " +
                (m.role === "user" ? "bg-blue-600 text-white" : "bg-white border")
              }
            >
              {m.content}
            </div>
            {m.data?.response_type === "table" && m.data.table && (
              <TableRenderer rows={m.data.table} />
            )}
            {m.data?.response_type === "chart" && m.data.chart && (
              <ChartRenderer chart={m.data.chart} />
            )}
            {m.data?.response_type === "confirm_write" && m.data.proposal_id && (
              <ConfirmWrite proposalId={m.data.proposal_id} text={m.data.text} />
            )}
          </div>
        ))}
        {loading && <p className="text-sm text-gray-400">Thinking...</p>}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 border-t pt-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask something..."
          className="flex-1 border rounded-full px-4 py-2 text-sm"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-blue-600 text-white text-sm px-4 py-2 rounded-full disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </main>
  );
}
