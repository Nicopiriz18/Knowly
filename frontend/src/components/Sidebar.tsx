"use client";

import { ClassInfo, MateriaInfo, deleteClass, deleteMateria, createMateria } from "@/lib/api";
import {
  GraduationCap,
  Plus,
  Trash2,
  BookOpen,
  ChevronRight,
  FolderOpen,
  X,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

interface SidebarProps {
  materias: MateriaInfo[];
  classes: ClassInfo[];
  selectedClass: string | null;
  selectedMateria: string | null;
  onSelectClass: (classId: string | null, materiaId: string | null) => void;
  onRefresh: () => void;
}

export default function Sidebar({
  materias,
  classes,
  selectedClass,
  selectedMateria,
  onSelectClass,
  onRefresh,
}: SidebarProps) {
  const [deleting, setDeleting] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showNewMateria, setShowNewMateria] = useState(false);
  const [newMateriaTitle, setNewMateriaTitle] = useState("");
  const [creatingMateria, setCreatingMateria] = useState(false);

  const toggleExpand = (materiaId: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(materiaId)) {
        next.delete(materiaId);
      } else {
        next.add(materiaId);
      }
      return next;
    });
  };

  const handleDeleteClass = async (e: React.MouseEvent, classId: string) => {
    e.stopPropagation();
    if (!confirm("Eliminar esta clase?")) return;
    setDeleting(classId);
    try {
      await deleteClass(classId);
      if (selectedClass === classId) onSelectClass(null, null);
      onRefresh();
    } finally {
      setDeleting(null);
    }
  };

  const handleDeleteMateria = async (e: React.MouseEvent, materiaId: string) => {
    e.stopPropagation();
    if (!confirm("Eliminar esta materia y todas sus clases?")) return;
    setDeleting(materiaId);
    try {
      await deleteMateria(materiaId);
      if (selectedMateria === materiaId) onSelectClass(null, null);
      onRefresh();
    } finally {
      setDeleting(null);
    }
  };

  const handleCreateMateria = async () => {
    const title = newMateriaTitle.trim();
    if (!title) return;
    setCreatingMateria(true);
    try {
      await createMateria(title);
      setNewMateriaTitle("");
      setShowNewMateria(false);
      onRefresh();
    } finally {
      setCreatingMateria(false);
    }
  };

  const classesByMateria = (materiaId: string) =>
    classes.filter((c) => c.materia_id === materiaId);

  const isAllSelected = selectedClass === null && selectedMateria === null;

  return (
    <aside className="w-[272px] h-screen bg-[#0d0d14] border-r border-white/[0.06] flex flex-col shrink-0">
      {/* Header */}
      <div className="px-5 py-5 border-b border-white/[0.06]">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-indigo-600/20 flex items-center justify-center">
            <GraduationCap className="w-[18px] h-[18px] text-indigo-400" />
          </div>
          <h1 className="text-[15px] font-semibold text-white tracking-tight">Knowly</h1>
        </Link>
      </div>

      {/* Materia & class list */}
      <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
        {/* All option */}
        <button
          onClick={() => onSelectClass(null, null)}
          className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-2.5 transition-all duration-150 ${
            isAllSelected
              ? "bg-white/[0.08] text-white"
              : "text-gray-500 hover:bg-white/[0.04] hover:text-gray-300"
          }`}
        >
          <BookOpen className="w-[15px] h-[15px] shrink-0" />
          <span className="text-[13px] font-medium truncate">Todas las materias</span>
        </button>

        {/* Divider */}
        <div className="h-px bg-white/[0.06] my-2 !mt-2 !mb-2" />

        {/* Add materia */}
        {showNewMateria ? (
          <div className="px-2 py-1.5">
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={newMateriaTitle}
                onChange={(e) => setNewMateriaTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateMateria();
                  if (e.key === "Escape") {
                    setShowNewMateria(false);
                    setNewMateriaTitle("");
                  }
                }}
                placeholder="Nombre..."
                autoFocus
                className="flex-1 bg-white/[0.06] border border-white/[0.08] rounded-lg px-2.5 py-1.5 text-[13px] text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 input-glow transition-all min-w-0"
              />
              <button
                onClick={handleCreateMateria}
                disabled={creatingMateria || !newMateriaTitle.trim()}
                className="p-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/[0.06] disabled:text-gray-600 text-white rounded-lg transition-colors shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  setShowNewMateria(false);
                  setNewMateriaTitle("");
                }}
                className="p-1.5 text-gray-600 hover:text-gray-400 transition-colors shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowNewMateria(true)}
            className="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2.5 text-gray-600 hover:bg-white/[0.04] hover:text-gray-400 transition-all duration-150"
          >
            <Plus className="w-[15px] h-[15px] shrink-0" />
            <span className="text-[13px] font-medium">Nueva materia</span>
          </button>
        )}

        {/* Materias */}
        {materias.map((mat) => {
          const isExpanded = expanded.has(mat.materia_id);
          const matClasses = classesByMateria(mat.materia_id);
          const isMateriaSelected =
            selectedMateria === mat.materia_id && selectedClass === null;

          return (
            <div key={mat.materia_id}>
              {/* Materia header */}
              <div
                className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-1.5 group transition-all duration-150 cursor-pointer ${
                  isMateriaSelected
                    ? "bg-white/[0.08] text-white"
                    : "text-gray-500 hover:bg-white/[0.04] hover:text-gray-300"
                }`}
              >
                <button
                  onClick={() => toggleExpand(mat.materia_id)}
                  className="shrink-0 p-0.5"
                >
                  <ChevronRight
                    className={`w-3 h-3 transition-transform duration-200 ${
                      isExpanded ? "rotate-90" : ""
                    }`}
                  />
                </button>
                <button
                  onClick={() => onSelectClass(null, mat.materia_id)}
                  className="flex-1 flex items-center gap-2 min-w-0"
                >
                  <FolderOpen className="w-[15px] h-[15px] shrink-0" />
                  <span className="text-[13px] font-medium truncate">
                    {mat.title}
                  </span>
                </button>
                <span className="text-[11px] text-gray-600 tabular-nums shrink-0">
                  {matClasses.length}
                </span>
                <button
                  onClick={(e) => handleDeleteMateria(e, mat.materia_id)}
                  disabled={deleting === mat.materia_id}
                  className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all shrink-0 p-0.5"
                  title="Eliminar materia"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>

              {/* Classes inside materia */}
              {isExpanded && (
                <div className="ml-4 mt-0.5 space-y-0.5 border-l border-white/[0.06] pl-2">
                  {matClasses.length === 0 ? (
                    <p className="text-[11px] text-gray-700 px-3 py-1.5">
                      Sin clases
                    </p>
                  ) : (
                    matClasses.map((cls) => (
                      <button
                        key={cls.class_id}
                        onClick={() =>
                          onSelectClass(cls.class_id, mat.materia_id)
                        }
                        className={`w-full text-left px-3 py-1.5 rounded-md flex items-center gap-2 group transition-all duration-150 ${
                          selectedClass === cls.class_id
                            ? "bg-indigo-600/15 text-indigo-300"
                            : "text-gray-600 hover:bg-white/[0.04] hover:text-gray-400"
                        }`}
                      >
                        <BookOpen className="w-3 h-3 shrink-0" />
                        <span className="text-[12px] font-medium truncate flex-1">
                          {cls.class_title}
                        </span>
                        <span className="text-[10px] text-gray-700 tabular-nums shrink-0">
                          {cls.chunk_count}
                        </span>
                        <button
                          onClick={(e) => handleDeleteClass(e, cls.class_id)}
                          disabled={deleting === cls.class_id}
                          className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all shrink-0"
                          title="Eliminar clase"
                        >
                          <Trash2 className="w-2.5 h-2.5" />
                        </button>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Bottom action */}
      <div className="p-3 border-t border-white/[0.06]">
        <Link
          href="/ingest"
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-[13px] font-medium rounded-xl transition-all duration-150 hover:shadow-lg hover:shadow-indigo-600/10"
        >
          <Plus className="w-4 h-4" />
          Agregar clase
        </Link>
      </div>
    </aside>
  );
}
