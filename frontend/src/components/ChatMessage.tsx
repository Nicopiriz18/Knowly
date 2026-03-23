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
      <div className="flex justify-end mb-5 animate-message-in">
        <div className="max-w-[70%]">
          <div className="px-4 py-2.5 rounded-2xl rounded-br-md bg-indigo-600 text-white text-[13px] leading-relaxed whitespace-pre-wrap">
            {content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6 animate-message-in">
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-7 h-7 rounded-lg bg-white/[0.06] flex items-center justify-center shrink-0 mt-0.5">
          <Bot className="w-3.5 h-3.5 text-indigo-400" />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="prose-chat text-[13px] text-gray-300 leading-relaxed">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => (
                  <p className="mb-3 last:mb-0">{children}</p>
                ),
                h1: ({ children }) => (
                  <h1 className="text-base font-semibold mb-2 mt-5 first:mt-0 text-white">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-sm font-semibold mb-2 mt-4 first:mt-0 text-white">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-[13px] font-semibold mb-1.5 mt-3 first:mt-0 text-gray-200">{children}</h3>
                ),
                ul: ({ children }) => (
                  <ul className="mb-3 space-y-1 pl-2">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="mb-3 space-y-1 pl-5 list-decimal marker:text-indigo-400/70">{children}</ol>
                ),
                li: ({ children, ...props }) => {
                  const ordered = (props as { ordered?: boolean }).ordered;
                  return ordered ? (
                    <li className="leading-relaxed pl-1">{children}</li>
                  ) : (
                    <li className="flex gap-2 items-start leading-relaxed list-none">
                      <span className="mt-[0.55em] w-1 h-1 rounded-full bg-indigo-400/60 shrink-0" />
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
                    <code className="block bg-white/[0.04] border border-white/[0.06] rounded-lg px-4 py-3 text-xs font-mono text-emerald-300/90 overflow-x-auto mb-3">
                      {children}
                    </code>
                  ) : (
                    <code className="bg-white/[0.08] rounded-md px-1.5 py-0.5 text-xs font-mono text-indigo-300">
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => (
                  <pre className="mb-3 overflow-x-auto">{children}</pre>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-indigo-500/30 pl-3 text-gray-400 italic mb-3">
                    {children}
                  </blockquote>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto mb-3 rounded-lg border border-white/[0.06]">
                    <table className="w-full text-xs">{children}</table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-white/[0.04] text-gray-400">{children}</thead>
                ),
                tbody: ({ children }) => (
                  <tbody className="divide-y divide-white/[0.06]">{children}</tbody>
                ),
                tr: ({ children }) => (
                  <tr className="hover:bg-white/[0.02] transition-colors">{children}</tr>
                ),
                th: ({ children }) => (
                  <th className="px-3 py-2 text-left font-medium text-indigo-300/80 whitespace-nowrap">{children}</th>
                ),
                td: ({ children }) => (
                  <td className="px-3 py-2 text-gray-400">{children}</td>
                ),
                hr: () => <hr className="border-white/[0.06] my-4" />,
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 decoration-indigo-400/30 transition-colors"
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
              <p className="text-[11px] text-gray-600 font-medium mb-2 uppercase tracking-wider">Fuentes</p>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {sources.map((source, idx) => (
                  <a
                    key={idx}
                    href={source.timestamp_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="min-w-[200px] max-w-[240px] bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 shrink-0 hover:border-white/[0.12] hover:bg-white/[0.05] transition-all duration-150 group block"
                  >
                    <p className="text-[12px] font-medium text-gray-300 truncate mb-1.5 group-hover:text-white transition-colors">
                      {source.class_title}
                    </p>
                    <div className="flex items-center gap-1 text-[11px] text-gray-600 mb-2">
                      <Clock className="w-3 h-3" />
                      <span>
                        {formatTime(source.start_time)} - {formatTime(source.end_time)}
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-600 line-clamp-2 mb-2">
                      {source.text.length > 100
                        ? source.text.slice(0, 100) + "..."
                        : source.text}
                    </p>
                    <span className="inline-flex items-center gap-1 text-[11px] text-indigo-400/80 group-hover:text-indigo-300 transition-colors">
                      <ExternalLink className="w-3 h-3" />
                      Ver en YouTube
                    </span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
