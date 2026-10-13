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
  LogOut,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";

interface SidebarProps {
  materias: MateriaInfo[];
  classes: ClassInfo[];
  selectedClass: string | null;
  selectedMateria: string | null;
  onSelectClass: (classId: string | null, materiaId: string | null) => void;
  onRefresh: () => void;
  // Mobile drawer state (the sidebar is always visible from md up)
  open: boolean;
  onClose: () => void;
}

export default function Sidebar({
  materias,
  classes,
  selectedClass,
  selectedMateria,
  onSelectClass,
  onRefresh,
  open,
  onClose,
}: SidebarProps) {
  const { user, logout } = useAuth();
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

  const select = (classId: string | null, materiaId: string | null) => {
    onSelectClass(classId, materiaId);
    onClose();
  };

  const classesByMateria = (materiaId: string) =>
    classes.filter((c) => c.materia_id === materiaId);

  const isAllSelected = selectedClass === null && selectedMateria === null;

  return (
    <>
    {/* Backdrop (mobile drawer) */}
    <div
      onClick={onClose}
      className={`fixed inset-0 z-30 bg-black/60 transition-opacity md:hidden ${
        open ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
    />
    <aside
      className={`fixed inset-y-0 left-0 z-40 w-[280px] max-w-[85vw] bg-gray-900 border-r border-gray-800 flex flex-col shrink-0 transition-[transform,visibility] duration-200 md:static md:h-dvh md:max-w-none md:visible md:translate-x-0 ${
        open ? "translate-x-0" : "-translate-x-full invisible"
      }`}
    >
      {/* Header */}
      <div className="p-5 border-b border-gray-800 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <GraduationCap className="w-7 h-7 text-indigo-500" />
          <h1 className="text-xl font-bold text-white">Knowly</h1>
        </Link>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors md:hidden"
          title="Cerrar menú"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Materia & class list */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {/* All option */}
        <button
          onClick={() => select(null, null)}
          className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-2.5 transition-colors ${
            isAllSelected
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-transparent"
          }`}
        >
          <BookOpen className="w-4 h-4 shrink-0" />
          <span className="text-sm font-medium truncate">Todas las materias</span>
        </button>

        {/* Add materia */}
        {showNewMateria ? (
          <div className="px-3 py-2">
            <div className="flex items-center gap-2">
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
                placeholder="Nombre de la materia..."
                autoFocus
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-base md:text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors min-w-0"
              />
              <button
                onClick={handleCreateMateria}
                disabled={creatingMateria || !newMateriaTitle.trim()}
                className="p-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-lg transition-colors shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  setShowNewMateria(false);
                  setNewMateriaTitle("");
                }}
                className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowNewMateria(true)}
            className="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2.5 text-gray-500 hover:bg-gray-800 hover:text-gray-300 border border-dashed border-gray-700 transition-colors"
          >
            <Plus className="w-4 h-4 shrink-0" />
            <span className="text-sm font-medium">Agregar materia</span>
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
                className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-2 group transition-colors cursor-pointer ${
                  isMateriaSelected
                    ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-transparent"
                }`}
              >
                <button
                  onClick={() => toggleExpand(mat.materia_id)}
                  className="shrink-0"
                >
                  <ChevronRight
                    className={`w-3.5 h-3.5 transition-transform ${
                      isExpanded ? "rotate-90" : ""
                    }`}
                  />
                </button>
                <button
                  onClick={() => select(null, mat.materia_id)}
                  className="flex-1 flex items-center gap-2 min-w-0"
                >
                  <FolderOpen className="w-4 h-4 shrink-0" />
                  <span className="text-sm font-medium truncate">
                    {mat.title}
                  </span>
                </button>
                <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded shrink-0">
                  {matClasses.length}
                </span>
                <button
                  onClick={(e) => handleDeleteMateria(e, mat.materia_id)}
                  disabled={deleting === mat.materia_id}
                  className="p-1 -m-1 md:opacity-0 md:group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all shrink-0"
                  title="Eliminar materia"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Classes inside materia */}
              {isExpanded && (
                <div className="ml-5 mt-0.5 space-y-0.5">
                  {matClasses.length === 0 ? (
                    <p className="text-xs text-gray-600 px-3 py-1.5">
                      Sin clases
                    </p>
                  ) : (
                    matClasses.map((cls) => (
                      <button
                        key={cls.class_id}
                        onClick={() =>
                          select(cls.class_id, mat.materia_id)
                        }
                        className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 group transition-colors ${
                          selectedClass === cls.class_id
                            ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20"
                            : "text-gray-500 hover:bg-gray-800 hover:text-gray-300 border border-transparent"
                        }`}
                      >
                        <BookOpen className="w-3.5 h-3.5 shrink-0" />
                        <span className="text-xs font-medium truncate flex-1">
                          {cls.class_title}
                        </span>
                        <span className="text-[10px] bg-gray-800 text-gray-600 px-1 py-0.5 rounded shrink-0">
                          {cls.chunk_count}
                        </span>
                        <button
                          onClick={(e) => handleDeleteClass(e, cls.class_id)}
                          disabled={deleting === cls.class_id}
                          className="p-1 -m-1 md:opacity-0 md:group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all shrink-0"
                          title="Eliminar clase"
                        >
                          <Trash2 className="w-3 h-3" />
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
      <div className="p-3 border-t border-gray-800">
        <Link
          href="/ingest"
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Agregar clase
        </Link>
        {user?.is_admin && (
          <Link
            href="/admin"
            className="mt-2 w-full flex items-center justify-center gap-2 px-4 py-2 text-gray-400 hover:bg-gray-800 hover:text-gray-200 text-sm font-medium rounded-lg transition-colors"
          >
            <ShieldCheck className="w-4 h-4" />
            Solicitudes de acceso
          </Link>
        )}
        {user && (
          <div className="mt-2 flex items-center gap-2 px-2 pt-2 border-t border-gray-800">
            <span className="flex-1 text-xs text-gray-500 truncate" title={user.email}>
              {user.email}
            </span>
            <button
              onClick={logout}
              className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors"
              title="Cerrar sesión"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </aside>
    </>
  );
}
