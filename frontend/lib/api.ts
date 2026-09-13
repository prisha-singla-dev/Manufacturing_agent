const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ChatResponse = {
  response_type: "text" | "table" | "chart" | "confirm_write";
  text: string;
  table: Record<string, any>[] | null;
  chart: { chart_type: string; x_key: string; y_key: string; data: Record<string, any>[] } | null;
  proposal_id: string | null;
  proposal_sql: string | null;
};

export async function sendMessage(message: string, persona: string, threadId: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, persona, thread_id: threadId }),
  });
  if (!res.ok) throw new Error(`Backend error: ${res.status}`);
  return res.json();
}

export async function confirmWrite(proposalId: string): Promise<{ status: string; explanation: string }> {
  const res = await fetch(`${API_URL}/confirm-write/${proposalId}`, { method: "POST" });
  if (!res.ok) throw new Error(`Confirm failed: ${res.status}`);
  return res.json();
}