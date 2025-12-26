import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { DeliverableDetails, MarkDeliveredInput } from '@/types/domain';
import { deliverablesApi } from '@/api/deliverables';
import { formatFileSize } from '@/utils/formatters';
import { format } from 'date-fns';
import { CheckCircle, X } from 'lucide-react';
import { Button, Input, Textarea } from '@/components/ui';

interface Props {
  deliverable: DeliverableDetails;
}

interface MarkDialogProps {
  deliverable: DeliverableDetails | null;
  onClose: () => void;
  onSubmit: (input: MarkDeliveredInput) => void;
  isSubmitting: boolean;
}

function MarkDeliveredDialog({ deliverable, onClose, onSubmit, isSubmitting }: MarkDialogProps) {
  const [proofUrl, setProofUrl] = useState('');
  const [proofNotes, setProofNotes] = useState('');

  if (!deliverable) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-lg rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Mark Delivered</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Deliverable ID: {deliverable.id}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="space-y-4">
          <Input
            type="url"
            label="Proof URL (optional)"
            value={proofUrl}
            onChange={(e) => setProofUrl(e.target.value)}
            placeholder="https://example.com/proof"
            helperText="Link to email confirmation, screenshot, or other proof"
          />
          <Textarea
            label="Delivery Notes (optional)"
            value={proofNotes}
            onChange={(e) => setProofNotes(e.target.value)}
            rows={3}
            placeholder="Add any relevant notes about the delivery..."
          />
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="success"
            disabled={isSubmitting}
            onClick={() =>
              onSubmit({
                deliveredAt: new Date().toISOString(),
                proofUrl: proofUrl || undefined,
                proofNotes: proofNotes || undefined,
              })
            }
          >
            <CheckCircle className="h-4 w-4" />
            {isSubmitting ? 'Marking Delivered...' : 'Mark Delivered'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function OverviewTab({ deliverable }: Props) {
  const [showMarkDialog, setShowMarkDialog] = useState(false);
  const queryClient = useQueryClient();

  const markDelivered = useMutation({
    mutationFn: (input: MarkDeliveredInput) => deliverablesApi.markDelivered(deliverable.id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deliverables'] });
      queryClient.invalidateQueries({ queryKey: ['deliverable-details', deliverable.id] });
      setShowMarkDialog(false);
    },
  });

  return (
    <div className="space-y-4 p-6">
      {/* Format & Size */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Format</div>
          <div className="mt-1 text-sm font-medium">{deliverable.format.toUpperCase()}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">File Size</div>
          <div className="mt-1 text-sm">{formatFileSize(deliverable.fileSizeBytes)}</div>
        </div>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Created</div>
          <div className="mt-1 text-sm">{format(new Date(deliverable.createdAt), 'PPp')}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Delivered</div>
          <div className="mt-1 text-sm">
            {deliverable.deliveredAt
              ? format(new Date(deliverable.deliveredAt), 'PPp')
              : <span className="text-slate-400">Not delivered</span>
            }
          </div>
        </div>
      </div>

      {/* Modified Date */}
      {deliverable.fileModifiedAt && (
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Last Modified</div>
          <div className="mt-1 text-sm">{format(new Date(deliverable.fileModifiedAt), 'PPp')}</div>
        </div>
      )}

      {/* Status */}
      <div>
        <div className="text-xs font-medium text-slate-500 uppercase">Status</div>
        <div className="mt-1 flex items-center gap-3">
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
            deliverable.status === 'delivered' ? 'bg-green-100 text-green-800' :
            deliverable.status === 'ready' ? 'bg-blue-100 text-blue-800' :
            'bg-slate-100 text-slate-800'
          }`}>
            {deliverable.status}
          </span>
          {deliverable.status !== 'delivered' && (
            <Button
              variant="success"
              size="sm"
              onClick={() => setShowMarkDialog(true)}
            >
              <CheckCircle className="h-4 w-4" />
              Mark Delivered
            </Button>
          )}
        </div>
      </div>

      {/* IDs */}
      <div className="pt-4 border-t border-slate-200">
        <div className="space-y-3">
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase">Deliverable ID</div>
            <div className="mt-1 font-mono text-xs text-slate-700">{deliverable.id}</div>
          </div>

          <div>
            <div className="text-xs font-medium text-slate-500 uppercase">Project ID</div>
            <div className="mt-1 font-mono text-xs text-slate-700">{deliverable.projectId}</div>
          </div>

          <div>
            <div className="text-xs font-medium text-slate-500 uppercase">Client ID</div>
            <div className="mt-1 font-mono text-xs text-slate-700">{deliverable.clientId}</div>
          </div>

          {deliverable.runId && (
            <div>
              <div className="text-xs font-medium text-slate-500 uppercase">Run ID</div>
              <div className="mt-1 font-mono text-xs text-slate-700">{deliverable.runId}</div>
            </div>
          )}
        </div>
      </div>

      {/* Path */}
      <div>
        <div className="text-xs font-medium text-slate-500 uppercase">File Path</div>
        <div className="mt-1 font-mono text-xs text-slate-700 break-all bg-slate-50 p-2 rounded">
          {deliverable.path}
        </div>
      </div>

      {/* Checksum */}
      {deliverable.checksum && (
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Checksum</div>
          <div className="mt-1 font-mono text-xs text-slate-700 break-all bg-slate-50 p-2 rounded">
            {deliverable.checksum}
          </div>
        </div>
      )}

      {/* Proof */}
      {(deliverable.proofUrl || deliverable.proofNotes) && (
        <div className="pt-4 border-t border-slate-200">
          <div className="text-xs font-medium text-slate-500 uppercase mb-2">Delivery Proof</div>
          {deliverable.proofUrl && (
            <div className="mb-2">
              <a
                href={deliverable.proofUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                View Proof
              </a>
            </div>
          )}
          {deliverable.proofNotes && (
            <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded">
              {deliverable.proofNotes}
            </div>
          )}
        </div>
      )}

      {/* Mark Delivered Dialog */}
      {showMarkDialog && (
        <MarkDeliveredDialog
          deliverable={deliverable}
          onClose={() => setShowMarkDialog(false)}
          onSubmit={(input) => markDelivered.mutate(input)}
          isSubmitting={markDelivered.isPending}
        />
      )}
    </div>
  );
}
