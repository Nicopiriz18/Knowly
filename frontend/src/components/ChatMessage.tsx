"use client";

import { Source } from "@/lib/api";
import { ExternalLink, Clock } from "lucide-react";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Message bubble */}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-indigo-600 text-white rounded-br-md"
              : "bg-gray-800 text-gray-100 rounded-bl-md border border-gray-700"
          }`}
        >
          {content}
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="mt-2 space-y-2">
            <p className="text-xs text-gray-500 font-medium px-1">Fuentes:</p>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {sources.map((source, idx) => (
                <div
                  key={idx}
                  className="min-w-[220px] max-w-[260px] bg-gray-850 bg-gray-900 border border-gray-700 rounded-xl p-3 shrink-0"
                >
                  <p className="text-xs font-semibold text-indigo-400 truncate mb-1">
                    {source.class_title}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
                    <Clock className="w-3 h-3" />
                    <span>
                      {formatTime(source.start_time)} - {formatTime(source.end_time)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mb-2 line-clamp-2">
                    {source.text.length > 100
                      ? source.text.slice(0, 100) + "..."
                      : source.text}
                  </p>
                  <a
                    href={source.timestamp_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Ver en YouTube
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
