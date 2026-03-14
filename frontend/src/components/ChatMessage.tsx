"use client";

import { Source } from "@/lib/api";
import { ExternalLink, Clock, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function ChatMessage({ role, content, sources, isStreaming }: ChatMessageProps) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-5">
        <div className="max-w-[70%]">
          <div className="px-4 py-2.5 rounded-2xl rounded-br-sm bg-indigo-600 text-white text-sm leading-relaxed whitespace-pre-wrap">
            {content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6">
      <div className="flex items-start gap-3 max-w-[85%]">
        {/* Avatar */}
        <div className="w-7 h-7 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0 mt-0.5">
          <Bot className="w-4 h-4 text-indigo-400" />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="prose-chat text-sm text-gray-200 leading-relaxed">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => (
                  <p className="mb-3 last:mb-0">{children}</p>
                ),
                h1: ({ children }) => (
                  <h1 className="text-base font-bold mb-2 mt-5 first:mt-0 text-white">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-sm font-bold mb-2 mt-4 first:mt-0 text-white">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-sm font-semibold mb-1.5 mt-3 first:mt-0 text-gray-100">{children}</h3>
                ),
                ul: ({ children }) => (
                  <ul className="mb-3 space-y-1 pl-2">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="mb-3 space-y-1 pl-5 list-decimal marker:text-indigo-400">{children}</ol>
                ),
                li: ({ children, ...props }) => {
                  const ordered = (props as { ordered?: boolean }).ordered;
                  return ordered ? (
                    <li className="leading-relaxed pl-1">{children}</li>
                  ) : (
                    <li className="flex gap-2 items-start leading-relaxed list-none">
                      <span className="mt-[0.45em] w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
                      <span className="flex-1">{children}</span>
                    </li>
                  );
                },
                strong: ({ children }) => (
                  <strong className="font-semibold text-white">{children}</strong>
                ),
                em: ({ children }) => (
                  <em className="italic text-gray-400">{children}</em>
                ),
                code: ({ children, className }) => {
                  const isBlock = className?.includes("language-");
                  return isBlock ? (
                    <code className="block bg-gray-900/80 border border-gray-800 rounded-lg px-4 py-3 text-xs font-mono text-green-300 overflow-x-auto mb-3">
                      {children}
                    </code>
                  ) : (
                    <code className="bg-gray-800 rounded px-1.5 py-0.5 text-xs font-mono text-indigo-300">
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => (
                  <pre className="mb-3 overflow-x-auto">{children}</pre>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-indigo-500/50 pl-3 text-gray-400 italic mb-3">
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="border-gray-800 my-4" />,
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 decoration-indigo-400/30"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-indigo-400 ml-0.5 streaming-cursor rounded-sm align-text-bottom" />
            )}
          </div>

          {/* Sources */}
          {sources && sources.length > 0 && !isStreaming && (
            <div className="mt-4 sources-appear">
              <p className="text-xs text-gray-500 font-medium mb-2">Fuentes</p>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {sources.map((source, idx) => (
                  <div
                    key={idx}
                    className="min-w-[200px] max-w-[240px] bg-gray-900/60 border border-gray-800 rounded-xl p-3 shrink-0 hover:border-gray-700 transition-colors"
                  >
                    <p className="text-xs font-medium text-indigo-400 truncate mb-1">
                      {source.class_title}
                    </p>
                    <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
                      <Clock className="w-3 h-3" />
                      <span>
                        {formatTime(source.start_time)} - {formatTime(source.end_time)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mb-2 line-clamp-2">
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
    </div>
  );
}
