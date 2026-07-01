import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Pencil, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button, Input } from '@/components/ui';
import { keywordsApi, type ClientKeyword, type KeywordType } from '@/api/keywords';

interface KeywordTypeTabProps {
  clientId: string;
  type: KeywordType;
  keywords: ClientKeyword[];
  label: string;
  maxCount?: number;
}

const DIFFICULTY_COLORS: Record<string, string> = {
  low: 'text-emerald-600 dark:text-emerald-400',
  medium: 'text-amber-600 dark:text-amber-400',
  high: 'text-rose-600 dark:text-rose-400',
};

const SOURCE_BADGE: Record<string, string> = {
  research_tool:
    'bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300',
  manual:
    'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400',
};

export function KeywordTypeTab({
  clientId,
  type,
  keywords,
  label,
  maxCount = 50,
}: KeywordTypeTabProps) {
  const qc = useQueryClient();
  const [newText, setNewText] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const invalidate = () => qc.invalidateQueries({ queryKey: ['client-keywords', clientId] });

  const addMutation = useMutation({
    mutationFn: (keyword: string) =>
      keywordsApi.addKeyword(clientId, { keyword, keywordType: type }),
    onSuccess: () => {
      setNewText('');
      invalidate();
    },
    onError: (err: Error) => toast.error(err.message ?? 'Could not add keyword'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, keyword }: { id: number; keyword: string }) =>
      keywordsApi.updateKeyword(clientId, id, { keyword }),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    },
    onError: (err: Error) => toast.error(err.message ?? 'Could not update keyword'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => keywordsApi.deleteKeyword(clientId, id),
    onSuccess: () => invalidate(),
    onError: (err: Error) => toast.error(err.message ?? 'Could not delete keyword'),
  });

  function handleAdd() {
    const text = newText.trim();
    if (!text || text.length < 2) return;
    addMutation.mutate(text);
  }

  function startEdit(kw: ClientKeyword) {
    setEditingId(kw.id);
    setEditText(kw.keyword);
  }

  function commitEdit(id: number) {
    const text = editText.trim();
    if (!text || text.length < 2) {
      setEditingId(null);
      return;
    }
    updateMutation.mutate({ id, keyword: text });
  }

  function handleDelete(id: number) {
    setPendingDelete(id);
    const tid = setTimeout(() => {
      deleteMutation.mutate(id);
      setPendingDelete(null);
    }, 5000);
    undoTimer.current = tid;
    toast('Keyword removed', {
      action: {
        label: 'Undo',
        onClick: () => {
          clearTimeout(tid);
          setPendingDelete(null);
        },
      },
      duration: 5000,
    });
  }

  const activeKeywords = keywords.filter(
    (k) => k.isActive && k.id !== pendingDelete
  );
  const atMax = activeKeywords.length >= maxCount;

  return (
    <div className="space-y-3">
      {/* Add row */}
      <div className="flex gap-2">
        <Input
          ref={inputRef}
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder={`Add ${label.toLowerCase()} keyword…`}
          disabled={atMax || addMutation.isPending}
          className="flex-1"
        />
        <Button
          variant="primary"
          size="sm"
          onClick={handleAdd}
          disabled={atMax || !newText.trim() || addMutation.isPending}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {atMax && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Maximum {maxCount} {label.toLowerCase()} keywords reached.
        </p>
      )}

      {/* Keyword list */}
      {activeKeywords.length === 0 ? (
        <p className="text-sm text-neutral-400 dark:text-neutral-500 py-4 text-center">
          No {label.toLowerCase()} keywords yet. Add one above.
        </p>
      ) : (
        <ul className="divide-y divide-neutral-100 dark:divide-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
          {activeKeywords.map((kw) => (
            <li
              key={kw.id}
              className="flex items-center gap-2 px-3 py-2 group"
            >
              {editingId === kw.id ? (
                <>
                  <Input
                    autoFocus
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitEdit(kw.id);
                      if (e.key === 'Escape') setEditingId(null);
                    }}
                    className="flex-1 h-7 text-sm"
                  />
                  <button
                    onClick={() => commitEdit(kw.id)}
                    className="text-emerald-600 hover:text-emerald-800 dark:text-emerald-400"
                    aria-label="Save"
                  >
                    <Check className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="text-neutral-400 hover:text-neutral-600"
                    aria-label="Cancel"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </>
              ) : (
                <>
                  <span className="flex-1 text-sm text-neutral-800 dark:text-neutral-200 truncate">
                    {kw.keyword}
                  </span>

                  {/* Research metadata (present on research-seeded keywords) */}
                  {kw.searchIntent && (
                    <span
                      className="hidden md:inline text-xs text-neutral-500 dark:text-neutral-400"
                      title="Search intent"
                    >
                      {kw.searchIntent}
                    </span>
                  )}
                  {kw.monthlyVolume && (
                    <span
                      className="hidden md:inline text-xs text-neutral-500 dark:text-neutral-400 tabular-nums"
                      title="Estimated monthly search volume"
                    >
                      {kw.monthlyVolume}/mo
                    </span>
                  )}
                  {kw.relevanceScore != null && (
                    <span
                      className="hidden lg:inline text-xs text-neutral-500 dark:text-neutral-400 tabular-nums"
                      title="Relevance score (1–10)"
                    >
                      rel {kw.relevanceScore.toFixed(1)}
                    </span>
                  )}

                  {kw.difficulty && (
                    <span
                      className={`hidden sm:inline text-xs font-medium ${DIFFICULTY_COLORS[kw.difficulty] ?? ''}`}
                    >
                      {kw.difficulty}
                    </span>
                  )}

                  <span
                    className={`hidden sm:inline text-xs px-1.5 py-0.5 rounded font-medium ${SOURCE_BADGE[kw.source] ?? SOURCE_BADGE.manual}`}
                  >
                    {kw.source === 'research_tool' ? 'research' : 'manual'}
                  </span>

                  <button
                    onClick={() => startEdit(kw)}
                    className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 transition-opacity"
                    aria-label="Edit keyword"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(kw.id)}
                    className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-rose-600 dark:hover:text-rose-400 transition-opacity"
                    aria-label="Delete keyword"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-neutral-400 dark:text-neutral-500">
        {activeKeywords.length} / {maxCount} {label.toLowerCase()} keywords
      </p>
    </div>
  );
}
