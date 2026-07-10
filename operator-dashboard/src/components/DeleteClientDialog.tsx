import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/Button';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { AlertTriangle, Download, Trash2 } from 'lucide-react';

interface DeleteClientDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clientId: string;
  clientName: string;
  /** Soft delete — archives the client, recoverable within 90 days */
  onConfirmDelete: () => Promise<void>;
  /** Hard delete — permanently erases all client data (GDPR right-to-erasure) */
  onConfirmPermanentDelete?: () => Promise<void>;
  onExportData?: () => Promise<void>;
}

export function DeleteClientDialog({
  open,
  onOpenChange,
  clientName,
  onConfirmDelete,
  onConfirmPermanentDelete,
  onExportData,
}: DeleteClientDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [hasExported, setHasExported] = useState(false);
  const [showPermanent, setShowPermanent] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  const handleExport = async () => {
    if (onExportData) {
      await onExportData();
      setHasExported(true);
    }
  };

  const handleArchive = async () => {
    setIsDeleting(true);
    try {
      await onConfirmDelete();
      onOpenChange(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const handlePermanentDelete = async () => {
    if (!onConfirmPermanentDelete) return;
    setIsDeleting(true);
    try {
      await onConfirmPermanentDelete();
      onOpenChange(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const isPermanentConfirmed = confirmText === clientName;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>
            <span className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Delete Client
            </span>
          </DialogTitle>
          <DialogDescription>
            You are about to delete <strong>{clientName}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2 text-sm">
            <h4 className="font-medium">What will be deleted:</h4>
            <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
              <li>Client profile and contact information</li>
              <li>All projects and generated content</li>
              <li>Research results and analytics data</li>
              <li>Post history and deliverables</li>
            </ul>
          </div>

          {onExportData && !hasExported && (
            <Button
              variant="outline"
              className="w-full"
              onClick={handleExport}
              disabled={isDeleting}
            >
              <Download className="h-4 w-4 mr-2" />
              Export Data Before Deletion
            </Button>
          )}

          {hasExported && (
            <Alert>
              <AlertDescription>
                ✓ Data exported successfully.
              </AlertDescription>
            </Alert>
          )}

          {onConfirmPermanentDelete && !showPermanent && (
            <button
              type="button"
              onClick={() => setShowPermanent(true)}
              className="text-xs text-red-600 dark:text-red-400 underline underline-offset-2 hover:no-underline"
            >
              Need to permanently erase all data (GDPR right-to-erasure)?
            </button>
          )}

          {showPermanent && (
            <div className="space-y-3 rounded-lg border border-red-300 dark:border-red-700 p-4 bg-red-50 dark:bg-red-900/10">
              <Alert variant="danger">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Permanent erasure — cannot be undone.</strong> All client data will be
                  immediately and permanently deleted. This satisfies GDPR Art. 17 and CCPA
                  deletion requests.
                </AlertDescription>
              </Alert>
              <p className="text-sm text-neutral-700 dark:text-neutral-300">
                Type <strong>{clientName}</strong> to confirm:
              </p>
              <input
                type="text"
                value={confirmText}
                onChange={e => setConfirmText(e.target.value)}
                placeholder={clientName}
                className="w-full rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                disabled={isDeleting}
              />
              <Button
                variant="danger"
                className="w-full"
                onClick={handlePermanentDelete}
                disabled={!isPermanentConfirmed || isDeleting}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                {isDeleting ? 'Deleting permanently...' : 'Permanently Delete All Data'}
              </Button>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleArchive}
            disabled={isDeleting}
          >
            {isDeleting ? 'Archiving...' : 'Archive Client (Recoverable)'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
