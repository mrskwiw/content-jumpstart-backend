import type { DeliverableDetails } from '@/types/domain';
import { formatFileSize } from '@/utils/formatters';
import { format } from 'date-fns';

interface Props {
  deliverable: DeliverableDetails;
}

export function OverviewTab({ deliverable }: Props) {
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
        <div className="mt-1">
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
            deliverable.status === 'delivered' ? 'bg-green-100 text-green-800' :
            deliverable.status === 'ready' ? 'bg-blue-100 text-blue-800' :
            'bg-slate-100 text-slate-800'
          }`}>
            {deliverable.status}
          </span>
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
    </div>
  );
}
