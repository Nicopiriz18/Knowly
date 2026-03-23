"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  ClassInfo,
  MateriaInfo,
  Source,
  getClasses,
  getMaterias,
  API,
} from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import ChatMessage from "@/components/ChatMessage";
import { Send, GraduationCap, Bot, Sparkles } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function Home() {
  const [materias, setMaterias] = useState<MateriaInfo[]>([]);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [selectedClass, setSelectedClass] = useState<string | null>(null);
  const [selectedMateria, setSelectedMateria] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isStreamingRef = useRef(false);

  const fetchData = useCallback(async () => {
    try {
      const [m, c] = await Promise.all([getMaterias(), getClasses()]);
      setMaterias(m);
      setClasses(c);
    } catch {
      // API might not be running
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelectClass = (
    classId: string | null,
    materiaId: string | null
  ) => {
    setSelectedClass(classId);
    setSelectedMateria(materiaId);
  };

  // Determine header label
  const headerLabel = (() => {
    if (selectedClass) {
      return (
        classes.find((c) => c.class_id === selectedClass)?.class_title ||
        selectedClass
      );
    }
    if (selectedMateria) {
      return (
        materias.find((m) => m.materia_id === selectedMateria)?.title ||
        selectedMateria
      );
    }
    return "Todas las materias";
  })();

  const sendMessage = async () => {
    const query = input.trim();
    if (!query || loading) return;

    setInput("");
    const userMessage: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          class_id: selectedClass,
          materia_id: selectedClass ? null : selectedMateria,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let receivedText = "";
      let displayedText = "";
      let sources: Source[] = [];
      let sseBuffer = "";

      const CHARS_PER_TICK = 3;
      const TICK_MS = 12;

      // Add empty assistant message
      setIsStreaming(true);
      isStreamingRef.current = true;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", sources: [] },
      ]);

      // Drip interval: moves chars from receivedText to displayedText
      const dripInterval = setInterval(() => {
        if (displayedText.length < receivedText.length) {
          const nextEnd = Math.min(
            displayedText.length + CHARS_PER_TICK,
            receivedText.length
          );
          displayedText = receivedText.slice(0, nextEnd);
          const snap = displayedText;
          const srcSnap = [...sources];
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = {
              role: "assistant",
              content: snap,
              sources: srcSnap.length > 0 ? srcSnap : undefined,
            };
            return copy;
          });
        } else if (!isStreamingRef.current) {
          // Stream ended and display caught up — stop interval
          clearInterval(dripInterval);
        }
      }, TICK_MS);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });

        const events = sseBuffer.split("\n\n");
        sseBuffer = events.pop() || "";

        for (const event of events) {
          const line = event.trim();
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);

          if (data.startsWith("[SOURCES]")) {
            try {
              sources = JSON.parse(data.slice(9));
            } catch {
              // ignore parse errors
            }
          } else if (data === "[DONE]") {
            // Stream complete
          } else {
            try {
              receivedText += JSON.parse(data);
            } catch {
              receivedText += data;
            }
          }
        }
      }

      // Stream ended — snap to final text immediately
      isStreamingRef.current = false;
      clearInterval(dripInterval);
      setIsStreaming(false);
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = {
          role: "assistant",
          content: receivedText,
          sources: sources.length > 0 ? sources : undefined,
        };
        return copy;
      });
    } catch {
      isStreamingRef.current = false;
      setIsStreaming(false);
      try {
        const res = await fetch(`${API}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            class_id: selectedClass,
            materia_id: selectedClass ? null : selectedMateria,
          }),
        });
        const data = await res.json();
        setMessages((prev) => {
          const filtered = prev.filter(
            (m, i) =>
              !(i === prev.length - 1 && m.role === "assistant" && !m.content)
          );
          return [
            ...filtered,
            {
              role: "assistant",
              content: data.answer,
              sources: data.sources,
            },
          ];
        });
      } catch {
        setMessages((prev) => {
          const filtered = prev.filter(
            (m, i) =>
              !(i === prev.length - 1 && m.role === "assistant" && !m.content)
          );
          return [
            ...filtered,
            {
              role: "assistant",
              content:
                "Lo siento, no pude conectar con el servidor. Verifica que el backend este corriendo.",
            },
          ];
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar
        materias={materias}
        classes={classes}
        selectedClass={selectedClass}
        selectedMateria={selectedMateria}
        onSelectClass={handleSelectClass}
        onRefresh={fetchData}
      />

      {/* Chat area */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#0a0a0f]">
        {/* Header */}
        <header className="h-12 border-b border-white/[0.06] flex items-center px-6 shrink-0">
          <h2 className="text-[13px] font-medium text-gray-500 truncate">
            {headerLabel}
          </h2>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mb-5">
                <Sparkles className="w-7 h-7 text-indigo-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2 tracking-tight">
                Bienvenido a Knowly
              </h3>
              <p className="text-[13px] text-gray-500 max-w-sm leading-relaxed">
                Pregunta lo que quieras sobre tus clases universitarias.
                Selecciona una materia o clase en el panel izquierdo.
              </p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-6 py-6">
              {messages.map((msg, idx) => (
                <ChatMessage
                  key={idx}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  isStreaming={
                    isStreaming &&
                    idx === messages.length - 1 &&
                    msg.role === "assistant"
                  }
                />
              ))}
              {loading &&
                messages[messages.length - 1]?.role === "user" && (
                  <div className="flex items-start gap-3 mb-6 animate-message-in">
                    <div className="w-7 h-7 rounded-lg bg-white/[0.06] flex items-center justify-center shrink-0">
                      <Bot className="w-3.5 h-3.5 text-indigo-400" />
                    </div>
                    <div className="flex items-center gap-2.5 py-1.5">
                      <div className="flex gap-1">
                        <span
                          className="w-1.5 h-1.5 bg-indigo-400 rounded-full thinking-pulse"
                          style={{ animationDelay: "0ms" }}
                        />
                        <span
                          className="w-1.5 h-1.5 bg-indigo-400 rounded-full thinking-pulse"
                          style={{ animationDelay: "300ms" }}
                        />
                        <span
                          className="w-1.5 h-1.5 bg-indigo-400 rounded-full thinking-pulse"
                          style={{ animationDelay: "600ms" }}
                        />
                      </div>
                      <span className="text-[11px] text-gray-600">Pensando...</span>
                    </div>
                  </div>
                )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="px-6 pb-5 pt-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex items-end gap-2.5 max-w-3xl mx-auto"
          >
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Escribe tu pregunta..."
                rows={1}
                className="w-full resize-none bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-3 text-[13px] text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500/40 input-glow transition-all"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/[0.05] disabled:text-gray-700 text-white rounded-xl transition-all duration-150 shrink-0 hover:shadow-lg hover:shadow-indigo-600/20"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
