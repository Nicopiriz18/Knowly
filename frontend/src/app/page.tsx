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
import { Send, GraduationCap } from "lucide-react";

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
      let assistantText = "";
      let sources: Source[] = [];
      let sseBuffer = "";
      let renderPending = false;

      // Add empty assistant message
      setIsStreaming(true);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", sources: [] },
      ]);

      const flushToUI = () => {
        renderPending = false;
        const updatedContent = assistantText;
        const updatedSources = [...sources];
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            role: "assistant",
            content: updatedContent,
            sources: updatedSources.length > 0 ? updatedSources : undefined,
          };
          return copy;
        });
      };

      const scheduleRender = () => {
        if (!renderPending) {
          renderPending = true;
          requestAnimationFrame(flushToUI);
        }
      };

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
              assistantText += JSON.parse(data);
            } catch {
              assistantText += data;
            }
          }
        }

        scheduleRender();
      }

      flushToUI();
      setIsStreaming(false);
    } catch {
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
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 border-b border-gray-800 flex items-center px-5 shrink-0 bg-gray-950">
          <h2 className="text-sm font-medium text-gray-300 truncate">
            {headerLabel}
          </h2>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <GraduationCap className="w-16 h-16 text-gray-700 mb-4" />
              <h3 className="text-lg font-medium text-gray-500 mb-2">
                Bienvenido a Knowly
              </h3>
              <p className="text-sm text-gray-600 max-w-md">
                Pregunta lo que quieras sobre tus clases universitarias.
                Selecciona una materia o clase en el panel izquierdo o pregunta
                sobre todas.
              </p>
            </div>
          ) : (
            <>
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
                  <div className="flex items-start gap-3 mb-6">
                    <div className="w-7 h-7 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0">
                      <div className="flex gap-1">
                        <span
                          className="w-1 h-1 bg-gray-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0ms" }}
                        />
                        <span
                          className="w-1 h-1 bg-gray-500 rounded-full animate-bounce"
                          style={{ animationDelay: "150ms" }}
                        />
                        <span
                          className="w-1 h-1 bg-gray-500 rounded-full animate-bounce"
                          style={{ animationDelay: "300ms" }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-800 bg-gray-950">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex items-end gap-3 max-w-3xl mx-auto"
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe tu pregunta..."
              rows={1}
              className="flex-1 resize-none bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-xl transition-colors shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
