"use client";

import { useEffect, useState, useRef } from "react";
import { sendMessage, ChatResponse } from "@/lib/api";
import TableRenderer from "@/components/TableRenderer";
import ChartRenderer from "@/components/ChartRenderer";
import ConfirmWrite from "@/components/ConfirmWrite";

const PERSONAS = [
  { value: "inventory_manager", label: "Inventory Manager", initial: "IM" },
  { value: "procurement_manager", label: "Procurement Manager", initial: "PM" },
  { value: "owner", label: "Business Owner", initial: "BO" },
];

const SUGGESTIONS: Record<string, string[]> = {
  inventory_manager: [
    "Which items are below their min stock level?",
    "Which locations hold the most stock value?",
    "What moved in and out of stock in the last 30 days?",
  ],
  procurement_manager: [
    "Which POs are pending receipt?",
    "Show vendor-wise total PO value",
    "Any PO line items with a quantity mismatch on receipt?",
  ],
  owner: [
    "What's our total procurement spend this year?",
    "Give me a quick health check on inventory and procurement",
    "Which vendors are we most dependent on by spend?",
  ],
};

type Message = { role: "user" | "assistant"; content: string; data?: ChatResponse; time: string };

function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function Avatar({ label, tone }: { label: string; tone: "user" | "assistant" }) {
  return (
    <div
      className={
        "w-7 h-7 rounded-md flex items-center justify-center text-[11px] font-medium font-mono-data shrink-0 " +
        (tone === "user" ? "bg-[var(--color-ink)] text-white" : "bg-[var(--color-steel)] text-white")
      }
    >
      {label}
    </div>
  );
}

export default function Page() {
  const [persona, setPersona] = useState(PERSONAS[0].value);
  const [threadId, setThreadId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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
  }, [messages, loading]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", content: text, time: nowLabel() }]);
    setInput("");
    setLoading(true);
    try {
      const data = await sendMessage(text, persona, threadId);
      setMessages((m) => [...m, { role: "assistant", content: data.text, data, time: nowLabel() }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Something went wrong: ${e.message}`, time: nowLabel() }]);
    } finally {
      setLoading(false);
    }
  }

  const currentPersona = PERSONAS.find((p) => p.value === persona)!;

  return (
    <main className="max-w-2xl mx-auto h-screen flex flex-col px-4">
      <header className="flex items-center gap-3 py-4 border-b" style={{ borderColor: "var(--color-border)" }}>
        <div className="w-8 h-8 rounded-md bg-[var(--color-ink)] text-white flex items-center justify-center text-xs font-mono-data">
          MA
        </div>
        <div className="flex-1">
          <h1 className="text-sm font-medium leading-tight">Manufacturing Agent</h1>
          <p className="text-xs text-[var(--color-slate)] leading-tight">Inventory & procurement</p>
        </div>
        <select
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          className="border rounded-md px-2 py-1.5 text-xs bg-[var(--color-surface)]"
          style={{ borderColor: "var(--color-border)" }}
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
          className="text-xs text-[var(--color-slate)] border rounded-md px-2 py-1.5 hover:bg-gray-50"
          style={{ borderColor: "var(--color-border)" }}
          title="Start a fresh thread if a conversation gets stuck"
        >
          New chat
        </button>
      </header>

      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 && (
          <div className="pt-6">
            <p className="text-sm text-[var(--color-slate)] mb-3">
              Ask a question as the {currentPersona.label.toLowerCase()}, or try:
            </p>
            <div className="flex flex-col gap-2 items-start">
              {SUGGESTIONS[persona].map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="text-sm text-left border rounded-lg px-3 py-2 hover:bg-white bg-[var(--color-surface)] transition-colors"
                  style={{ borderColor: "var(--color-border)" }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={"flex gap-2 msg-enter " + (m.role === "user" ? "flex-row-reverse" : "")}>
            <Avatar label={m.role === "user" ? currentPersona.initial : "AI"} tone={m.role} />
            <div className={"flex flex-col max-w-[80%] " + (m.role === "user" ? "items-end" : "items-start")}>
              <div
                className={
                  "rounded-2xl px-4 py-2 text-sm leading-relaxed " +
                  (m.role === "user"
                    ? "bg-[var(--color-ink)] text-white rounded-tr-sm"
                    : "bg-[var(--color-surface)] border rounded-tl-sm")
                }
                style={m.role === "assistant" ? { borderColor: "var(--color-border)" } : undefined}
              >
                {m.content}
              </div>
              <span className="text-[10px] text-[var(--color-slate)] mt-1 px-1">{m.time}</span>

              {m.data?.response_type === "table" && m.data.table && <TableRenderer rows={m.data.table} />}
              {m.data?.response_type === "chart" && m.data.chart && <ChartRenderer chart={m.data.chart} />}
              {m.data?.response_type === "confirm_write" && m.data.proposal_id && (
                <ConfirmWrite proposalId={m.data.proposal_id} text={m.data.text} />
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-2">
            <Avatar label="AI" tone="assistant" />
            <div className="bg-[var(--color-surface)] border rounded-2xl rounded-tl-sm px-4 py-3" style={{ borderColor: "var(--color-border)" }}>
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-slate)] typing-dot" />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-slate)] typing-dot" />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-slate)] typing-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 border-t py-3" style={{ borderColor: "var(--color-border)" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder={`Ask about ${currentPersona.label.toLowerCase()} data...`}
          className="flex-1 border rounded-full px-4 py-2 text-sm outline-none focus:ring-2"
          style={{ borderColor: "var(--color-border)" }}
        />
        <button
          onClick={() => send(input)}
          disabled={loading}
          className="bg-[var(--color-steel)] text-white text-sm px-4 py-2 rounded-full disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </main>
  );
}
