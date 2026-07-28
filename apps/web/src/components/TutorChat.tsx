"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { authFetch } from "@/lib/auth";

interface TutorChatProps {
  curriculumId: number;
  getCurrentTime: () => number;
}

interface Message {
  role: "user" | "model";
  content: string;
}

export default function TutorChat({ curriculumId, getCurrentTime }: TutorChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "model", content: "Hi! I'm your Socratic Tutor. Got a question about this video? Ask me and I'll look at the exact timestamp you're currently on." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg = input;
    setInput("");
    
    const newMessages = [...messages, { role: "user", content: userMsg } as Message];
    setMessages(newMessages);
    setLoading(true);
    
    try {
      const video_time = getCurrentTime();
      
      const res = await authFetch(`/api/v1/curricula/${curriculumId}/tutor`, {
        method: "POST",
        body: JSON.stringify({
          message: userMsg,
          video_time: video_time,
          chat_history: messages.slice(1) // exclude initial greeting
        })
      });
      
      if (!res.ok) throw new Error("Failed to get response");
      
      const data = await res.json();
      setMessages([...newMessages, { role: "model", content: data.response }]);
    } catch (err) {
      setMessages([...newMessages, { role: "model", content: "Sorry, I ran into an error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[500px] w-full rounded-xl border border-ink/10 bg-white shadow-sm overflow-hidden">
      <div className="flex-1 p-4 overflow-y-auto space-y-4" ref={scrollRef}>
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${msg.role === "user" ? "bg-indigo-600 text-white" : "bg-sky-100 text-sky-600"}`}>
              {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2 ${msg.role === "user" ? "bg-indigo-600 text-white rounded-tr-sm" : "bg-ink/5 text-ink rounded-tl-sm"}`}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3 flex-row">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-600">
              <Bot size={16} />
            </div>
            <div className="max-w-[80%] rounded-2xl px-4 py-2 bg-ink/5 text-ink rounded-tl-sm flex items-center">
              <Loader2 className="h-4 w-4 animate-spin text-ink-soft" />
            </div>
          </div>
        )}
      </div>
      
      <div className="p-4 border-t border-ink/10 bg-ink/5">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the code on screen..."
            className="w-full rounded-full border border-ink/10 bg-white px-4 py-3 pr-12 text-sm shadow-sm outline-none transition focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-white transition hover:bg-indigo-700 disabled:opacity-50"
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}
