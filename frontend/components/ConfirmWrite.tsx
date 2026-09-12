"use client";

import { useState } from "react";
import { confirmWrite } from "@/lib/api";

export default function ConfirmWrite({ proposalId, text }: { proposalId: string; text: string }) {
  const [status, setStatus] = useState<"pending" | "confirming" | "done" | "error">("pending");
  const [resultMsg, setResultMsg] = useState("");

  async function handleConfirm() {
    setStatus("confirming");
    try {
      const res = await confirmWrite(proposalId);
      setResultMsg(res.explanation || "Write executed.");
      setStatus("done");
    } catch (e: any) {
      setResultMsg(e.message);
      setStatus("error");
    }
  }

  return (
    <div className="mt-2 border-2 border-amber-400 bg-amber-50 rounded-lg p-3">
      <p className="text-sm text-amber-900 mb-2">⚠️ This will write to the database: {text}</p>
      {status === "pending" && (
        <button
          onClick={handleConfirm}
          className="bg-amber-600 text-white text-sm px-3 py-1.5 rounded hover:bg-amber-700"
        >
          Confirm write
        </button>
      )}
      {status === "confirming" && <p className="text-sm text-gray-500">Executing...</p>}
      {status === "done" && <p className="text-sm text-green-700">✅ {resultMsg}</p>}
      {status === "error" && <p className="text-sm text-red-700">❌ {resultMsg}</p>}
    </div>
  );
}
