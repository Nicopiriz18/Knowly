"use client";

import { ClassInfo, deleteClass } from "@/lib/api";
import { GraduationCap, Plus, Trash2, BookOpen } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

interface SidebarProps {
  classes: ClassInfo[];
  selectedClass: string | null;
  onSelectClass: (id: string | null) => void;
  onRefresh: () => void;
}

export default function Sidebar({
  classes,
  selectedClass,
  onSelectClass,
  onRefresh,
}: SidebarProps) {
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleDelete = async (e: React.MouseEvent, classId: string) => {
    e.stopPropagation();
    if (!confirm("Eliminar esta clase?")) return;
    setDeleting(classId);
    try {
      await deleteClass(classId);
      if (selectedClass === classId) onSelectClass(null);
      onRefresh();
    } finally {
      setDeleting(null);
    }
  };

  return (
    <aside className="w-[280px] h-screen bg-gray-900 border-r border-gray-800 flex flex-col shrink-0">
      {/* Header */}
      <div className="p-5 border-b border-gray-800">
        <Link href="/" className="flex items-center gap-2.5">
          <GraduationCap className="w-7 h-7 text-indigo-500" />
          <h1 className="text-xl font-bold text-white">Knowly</h1>
        </Link>
      </div>

      {/* Class list */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {/* All classes option */}
        <button
          onClick={() => onSelectClass(null)}
          className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-2.5 transition-colors ${
            selectedClass === null
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-transparent"
          }`}
        >
          <BookOpen className="w-4 h-4 shrink-0" />
          <span className="text-sm font-medium truncate">Todas las clases</span>
        </button>

        {/* Individual classes */}
        {classes.map((cls) => (
          <button
            key={cls.class_id}
            onClick={() => onSelectClass(cls.class_id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-2.5 group transition-colors ${
              selectedClass === cls.class_id
                ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                : "text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-transparent"
            }`}
          >
            <BookOpen className="w-4 h-4 shrink-0" />
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium truncate block">
                {cls.class_title}
              </span>
            </div>
            <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded shrink-0">
              {cls.chunk_count}
            </span>
            <button
              onClick={(e) => handleDelete(e, cls.class_id)}
              disabled={deleting === cls.class_id}
              className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all shrink-0"
              title="Eliminar clase"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </button>
        ))}
      </nav>

      {/* Bottom action */}
      <div className="p-3 border-t border-gray-800">
        <Link
          href="/ingest"
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Agregar clase
        </Link>
      </div>
    </aside>
  );
}
