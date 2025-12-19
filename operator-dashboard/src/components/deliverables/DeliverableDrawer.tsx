import { DialogHTMLAttributes } from 'react';
import type { Deliverable } from '@/types/domain';
import { X } from 'lucide-react';

interface Props extends DialogHTMLAttributes<HTMLDivElement> {
  deliverable: Deliverable | null;
  onClose: () => void;
}

export function DeliverableDrawer({ deliverable, onClose }: Props) {
  if (!deliverable) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/30">
      <div className="h-full w-full max-w-md bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">Deliverable {deliverable.id}</p>
            <p className="text-xs text-slate-500">{deliverable.format.toUpperCase()}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-800">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-3 px-4 py-3 text-sm text-slate-700">
          <div>
            <div className="text-xs uppercase text-slate-500">Path</div>
            <div className="font-mono text-xs text-slate-800">{deliverable.path}</div>
          </div>
          <div>
            <div className="text-xs uppercase text-slate-500">Run ID</div>
            <div className="text-slate-800">{deliverable.runId || '—'}</div>
          </div>
          <div>
            <div className="text-xs uppercase text-slate-500">Checksum</div>
            <div className="text-slate-800">{deliverable.checksum || 'pending'}</div>
          </div>
          <div>
            <div className="text-xs uppercase text-slate-500">Status</div>
            <div className="text-slate-800">{deliverable.status}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
