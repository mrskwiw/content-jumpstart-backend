import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Download, Upload, RefreshCw, HardDrive, Database, X, GitMerge } from 'lucide-react';

interface MergePreviewResult {
  success: boolean;
  dry_run: boolean;
  message: string;
  merged: Record<string, number>;
  skipped: Record<string, number>;
  total_merged: number;
  total_skipped: number;
  user_mapping: Record<string, string>;
  warnings: string[];
}

async function triggerBackupDownload(): Promise<void> {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/database/backup', { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    let detail = `Request failed: ${response.status} ${response.statusText}`;
    try { const err = await response.json(); detail = err.detail || detail; } catch { /* not JSON */ }
    throw new Error(detail);
  }
  const blob = await response.blob();
  const contentDisposition = response.headers.get('Content-Disposition');
  const filename = contentDisposition ? contentDisposition.split('filename=')[1].replace(/"/g, '') : `jumpstart_backup_${new Date().toISOString().slice(0, 10)}.db`;
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  window.URL.revokeObjectURL(url); document.body.removeChild(a);
}

export function DatabaseTab() {
  const queryClient = useQueryClient();
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
  const [mergeFile, setMergeFile] = useState<File | null>(null);
  const [showMergeConfirm, setShowMergeConfirm] = useState(false);
  const [mergePreview, setMergePreview] = useState<MergePreviewResult | null>(null);
  const [restorePoints, setRestorePoints] = useState<Array<{ filename: string; path: string; size_bytes: number; created_at: number }>>([]);
  const [showRestorePointsModal, setShowRestorePointsModal] = useState(false);

  const downloadBackupMutation = useMutation({
    mutationFn: triggerBackupDownload,
    onError: (error: Error) => alert(`Backup failed: ${error.message}`),
  });

  const restoreDatabaseMutation = useMutation({
    mutationFn: async (file: File) => {
      const token = localStorage.getItem('access_token');
      const formData = new FormData(); formData.append('file', file);
      const response = await fetch('/api/database/restore', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData });
      if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Failed to restore database'); }
      return response.json();
    },
    onSuccess: async () => {
      const token = localStorage.getItem('access_token');
      try {
        const response = await fetch('/api/database/restore-points', { headers: { Authorization: `Bearer ${token}` } });
        if (response.ok) { const data = await response.json(); setRestorePoints(data.restore_points || []); }
      } catch { /* ignore */ }
      queryClient.clear();
      setShowRestoreConfirm(false); setUploadFile(null);
      alert('Database restored successfully. You can now undo this restore using the restore points below.');
      setShowRestorePointsModal(true);
    },
    onError: (error: Error) => alert(`Restore failed: ${error.message}`),
  });

  const revertToRestorePointMutation = useMutation({
    mutationFn: async (filename: string) => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/database/restore-to-point?filename=${encodeURIComponent(filename)}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Failed to revert'); }
      return response.json();
    },
    onSuccess: () => { queryClient.clear(); setShowRestorePointsModal(false); alert('Database reverted to previous state successfully. Please refresh the page.'); },
    onError: (error: Error) => alert(`Revert failed: ${error.message}`),
  });

  const previewMergeMutation = useMutation({
    mutationFn: async (file: File): Promise<MergePreviewResult> => {
      const token = localStorage.getItem('access_token');
      const formData = new FormData(); formData.append('file', file);
      const response = await fetch('/api/database/merge?dry_run=true', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData });
      if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Preview failed'); }
      return response.json();
    },
    onSuccess: data => setMergePreview(data),
    onError: (error: Error) => alert(`Merge preview failed: ${error.message}`),
  });

  const executeMergeMutation = useMutation({
    mutationFn: async (file: File): Promise<MergePreviewResult> => {
      const token = localStorage.getItem('access_token');
      const formData = new FormData(); formData.append('file', file);
      const response = await fetch('/api/database/merge', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData });
      if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Merge failed'); }
      return response.json();
    },
    onSuccess: data => {
      queryClient.invalidateQueries();
      setShowMergeConfirm(false); setMergeFile(null); setMergePreview(null);
      alert(`Merge complete: ${data.total_merged} records imported${data.total_skipped > 0 ? `, ${data.total_skipped} duplicates skipped` : ''}.`);
    },
    onError: (error: Error) => alert(`Merge failed: ${error.message}`),
  });

  return (
    <>
      <div className="space-y-4">
        {/* Backup */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Database Backup</h3>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">Download a complete backup of your database. This includes all clients, projects, posts, runs, and deliverables.</p>
          <button onClick={() => downloadBackupMutation.mutate()} disabled={downloadBackupMutation.isPending} className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50">
            {downloadBackupMutation.isPending ? <><RefreshCw className="h-4 w-4 animate-spin" />Creating Backup...</> : <><Download className="h-4 w-4" />Download Database Backup</>}
          </button>
        </div>

        {/* Restore */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Database Restore</h3>
          <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 mb-4">
            <div className="flex gap-2"><AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" /><div className="text-xs text-amber-700 dark:text-amber-300"><strong>Warning:</strong> Restoring a database backup will replace all current data. You can undo the restore operation using restore points.</div></div>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Select Backup File (.db)</label>
              <input type="file" accept=".db" onChange={e => { const file = e.target.files?.[0]; if (file) setUploadFile(file); }} className="block w-full text-sm text-neutral-500 dark:text-neutral-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 dark:file:bg-primary-900/20 file:text-primary-700 dark:file:text-primary-400 hover:file:bg-primary-100 dark:hover:file:bg-primary-900/30 cursor-pointer" />
            </div>
            {uploadFile && (
              <div className="flex items-center justify-between rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3">
                <div className="flex items-center gap-2"><Database className="h-4 w-4 text-neutral-500 dark:text-neutral-400" /><span className="text-sm text-neutral-700 dark:text-neutral-300">{uploadFile.name}</span><span className="text-xs text-neutral-500 dark:text-neutral-400">({(uploadFile.size / 1024).toFixed(1)} KB)</span></div>
                <button aria-label="Remove backup file" onClick={() => setUploadFile(null)} className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300"><X className="h-4 w-4" /></button>
              </div>
            )}
            <button onClick={() => setShowRestoreConfirm(true)} disabled={!uploadFile || restoreDatabaseMutation.isPending} className="w-full rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50">
              <Upload className="inline h-4 w-4 mr-2" />Restore Database from Backup
            </button>
            <button onClick={async () => { const token = localStorage.getItem('access_token'); try { const response = await fetch('/api/database/restore-points', { headers: { Authorization: `Bearer ${token}` } }); if (response.ok) { const data = await response.json(); setRestorePoints(data.restore_points || []); setShowRestorePointsModal(true); } } catch { alert('Failed to fetch restore points'); } }} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">
              <HardDrive className="inline h-4 w-4 mr-2" />View Restore Points (Undo)
            </button>
          </div>
        </div>

        {/* Merge */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-1">Merge from Backup</h3>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">Import clients, projects, posts, and related content from another database backup without replacing your current users, credits, or settings. Duplicate records are skipped automatically.</p>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Select Backup File (.db)</label>
              <input type="file" accept=".db" onChange={e => { setMergeFile(e.target.files?.[0] ?? null); setMergePreview(null); }} className="block w-full text-sm text-neutral-500 dark:text-neutral-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 dark:file:bg-primary-900/20 file:text-primary-700 dark:file:text-primary-400 hover:file:bg-primary-100 dark:hover:file:bg-primary-900/30 cursor-pointer" />
            </div>
            {mergeFile && (
              <div className="flex items-center justify-between rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3">
                <div className="flex items-center gap-2"><Database className="h-4 w-4 text-neutral-500 dark:text-neutral-400" /><span className="text-sm text-neutral-700 dark:text-neutral-300">{mergeFile.name}</span><span className="text-xs text-neutral-500 dark:text-neutral-400">({(mergeFile.size / 1024).toFixed(1)} KB)</span></div>
                <button aria-label="Remove merge file" onClick={() => { setMergeFile(null); setMergePreview(null); }} className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300"><X className="h-4 w-4" /></button>
              </div>
            )}
            <button onClick={() => mergeFile && previewMergeMutation.mutate(mergeFile)} disabled={!mergeFile || previewMergeMutation.isPending || executeMergeMutation.isPending} className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50">
              {previewMergeMutation.isPending ? <><RefreshCw className="h-4 w-4 animate-spin" />Analyzing...</> : <><GitMerge className="h-4 w-4" />Preview Merge</>}
            </button>

            {mergePreview && (
              <div className="rounded-lg border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 p-4 space-y-3">
                <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Preview: {mergePreview.total_merged} records to import, {mergePreview.total_skipped} duplicates to skip</p>
                {Object.keys(mergePreview.merged).length > 0 && (<div><p className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-1">Will import:</p><div className="grid grid-cols-2 gap-x-4 gap-y-0.5">{Object.entries(mergePreview.merged).map(([table, count]) => <div key={table} className="flex justify-between text-xs text-blue-700 dark:text-blue-400"><span className="capitalize">{table.replace('_', ' ')}</span><span className="font-medium">{count}</span></div>)}</div></div>)}
                {Object.keys(mergePreview.skipped).length > 0 && (<div><p className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-1">Will skip (duplicates):</p><div className="grid grid-cols-2 gap-x-4 gap-y-0.5">{Object.entries(mergePreview.skipped).map(([table, count]) => <div key={table} className="flex justify-between text-xs text-blue-600 dark:text-blue-500"><span className="capitalize">{table.replace('_', ' ')}</span><span>{count}</span></div>)}</div></div>)}
                {mergePreview.warnings.length > 0 && (<div className="space-y-1">{mergePreview.warnings.map((w, i) => <div key={i} className="flex gap-2 text-xs text-amber-700 dark:text-amber-400"><AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" /><span>{w}</span></div>)}</div>)}
                {mergePreview.total_merged > 0 ? (
                  <button onClick={() => setShowMergeConfirm(true)} disabled={executeMergeMutation.isPending} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 dark:bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50"><GitMerge className="h-4 w-4" />Confirm Merge</button>
                ) : (
                  <p className="text-xs text-blue-600 dark:text-blue-400">Nothing to import — all records already exist in the current database.</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* DB Info */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Database Information</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-neutral-600 dark:text-neutral-400">Database Type:</span><span className="font-medium text-neutral-900 dark:text-neutral-100">SQLite</span></div>
            <div className="flex justify-between"><span className="text-neutral-600 dark:text-neutral-400">Backup Location:</span><span className="font-mono text-xs text-neutral-500 dark:text-neutral-400">data/backups/</span></div>
          </div>
        </div>
      </div>

      {/* Restore Confirm Modal */}
      {showRestoreConfirm && uploadFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
          <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
            <div className="flex items-start gap-4 mb-6"><div className="rounded-full bg-red-100 dark:bg-red-900/20 p-3"><AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" /></div><div><h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Confirm Database Restore</h3><p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">This will replace all current data with the backup file. This action cannot be undone.</p><p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mt-3">Restoring: {uploadFile.name}</p></div></div>
            <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 mb-6"><p className="text-xs text-amber-700 dark:text-amber-300">After restore, you can undo this operation using the restore points feature.</p></div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowRestoreConfirm(false)} disabled={restoreDatabaseMutation.isPending} className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">Cancel</button>
              <button onClick={() => restoreDatabaseMutation.mutate(uploadFile)} disabled={restoreDatabaseMutation.isPending} className="inline-flex items-center gap-2 rounded-lg bg-red-600 dark:bg-red-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 dark:hover:bg-red-600 disabled:opacity-50">
                {restoreDatabaseMutation.isPending ? <><RefreshCw className="h-4 w-4 animate-spin" />Restoring...</> : <><Upload className="h-4 w-4" />Restore Database</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Confirm Modal */}
      {showMergeConfirm && mergeFile && mergePreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
          <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
            <div className="flex items-start gap-4 mb-6"><div className="rounded-full bg-blue-100 dark:bg-blue-900/20 p-3"><GitMerge className="h-6 w-6 text-blue-600 dark:text-blue-400" /></div><div><h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Confirm Database Merge</h3><p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">This will import {mergePreview.total_merged} records from <span className="font-medium">{mergeFile.name}</span>. Your current users and credits will not be affected.</p></div></div>
            {mergePreview.warnings.length > 0 && <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 mb-6 space-y-1">{mergePreview.warnings.map((w, i) => <div key={i} className="flex gap-2 text-xs text-amber-700 dark:text-amber-300"><AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" /><span>{w}</span></div>)}</div>}
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowMergeConfirm(false)} disabled={executeMergeMutation.isPending} className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">Cancel</button>
              <button onClick={() => executeMergeMutation.mutate(mergeFile)} disabled={executeMergeMutation.isPending} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 dark:bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50">
                {executeMergeMutation.isPending ? <><RefreshCw className="h-4 w-4 animate-spin" />Merging...</> : <><GitMerge className="h-4 w-4" />Merge Database</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Restore Points Modal */}
      {showRestorePointsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
          <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
            <div className="flex items-start gap-4 mb-6"><div className="rounded-full bg-blue-100 dark:bg-blue-900/20 p-3"><HardDrive className="h-6 w-6 text-blue-600 dark:text-blue-400" /></div><div><h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Restore Points</h3><p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Snapshots saved before each restore. Use Undo to revert to a previous state.</p></div></div>
            <div className="max-h-64 overflow-y-auto mb-6 space-y-2">
              {restorePoints.length === 0 && <p className="text-sm text-neutral-500 dark:text-neutral-400 text-center py-6">No restore points available. They are created automatically when you restore a database.</p>}
              {restorePoints.map(point => (
                <div key={point.filename} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex-1"><p className="text-xs font-medium text-neutral-900 dark:text-neutral-100 truncate">{point.filename}</p><p className="text-xs text-neutral-500 dark:text-neutral-400">{(point.size_bytes / 1024 / 1024).toFixed(1)} MB • {new Date(point.created_at * 1000).toLocaleString()}</p></div>
                    <button onClick={() => revertToRestorePointMutation.mutate(point.filename)} disabled={revertToRestorePointMutation.isPending} className="ml-2 px-3 py-1 text-xs font-medium rounded text-white bg-red-600 dark:bg-red-500 hover:bg-red-700 dark:hover:bg-red-600 disabled:opacity-50">
                      {revertToRestorePointMutation.isPending ? 'Reverting...' : 'Undo'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-3"><button onClick={() => setShowRestorePointsModal(false)} disabled={revertToRestorePointMutation.isPending} className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">Keep This Restore</button></div>
          </div>
        </div>
      )}
    </>
  );
}
