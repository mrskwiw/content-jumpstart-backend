import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { distributionApi, PlatformCredential } from '@/api/distribution';
import { clientsApi } from '@/api/clients';

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  twitter: 'Twitter / X',
  facebook: 'Facebook',
  instagram: 'Instagram',
  tiktok: 'TikTok',
  youtube: 'YouTube',
};

export default function Connections() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const connected = params.get('connected');
  const error = params.get('error');

  const status = useQuery({ queryKey: ['oauth-status'], queryFn: distributionApi.oauthStatus });
  const creds = useQuery({ queryKey: ['credentials'], queryFn: distributionApi.listCredentials });
  const clients = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() });

  // MULTICLIENT-01: scope a NEW connection to a specific client (empty = account-level,
  // shared across all clients). The backend already binds this into the signed OAuth state.
  const [connectClientId, setConnectClientId] = useState('');
  const clientName = (id?: string | null) =>
    id ? (clients.data ?? []).find((c) => c.id === id)?.name ?? 'Unknown client' : 'Account-level';

  const startConnect = useMutation({
    mutationFn: (platform: string) =>
      distributionApi.oauthStart(platform, connectClientId || undefined),
    onSuccess: (url) => {
      window.location.href = url;
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => distributionApi.deleteCredential(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['credentials'] }),
  });

  const platforms = status.data?.all ?? [];
  const configured = new Set(status.data?.configured ?? []);
  // A platform can now have multiple credentials — one per client (+ an account-level
  // one, client_id=null) — under the backend's (user_id, client_id, platform) unique
  // constraint. So we list credentials flat and label each by its client.
  const allCreds = creds.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Connected accounts
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Connect a social account to publish and measure content. A platform is only connectable
          once its OAuth app credentials are configured on the server.
        </p>
      </div>

      {connected && (
        <Alert>
          <AlertDescription>
            Connected {PLATFORM_LABELS[connected] ?? connected}. You can now schedule posts to it.
          </AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="danger">
          <AlertDescription>Connection failed: {error}</AlertDescription>
        </Alert>
      )}

      {/* Scope a new connection to a client (or account-level). */}
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <label htmlFor="connect-client" className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Connect a new account for:
        </label>
        <select
          id="connect-client"
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
          value={connectClientId}
          onChange={(e) => setConnectClientId(e.target.value)}
        >
          <option value="">Account-level (all clients)</option>
          {(clients.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Each client can have its own account per platform.
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {platforms.map((platform) => {
          const canConnect = configured.has(platform);
          return (
            <Card key={platform}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{PLATFORM_LABELS[platform] ?? platform}</CardTitle>
                  <Badge variant={canConnect ? 'secondary' : 'default'}>
                    {canConnect ? 'Available' : 'Not configured'}
                  </Badge>
                </div>
                <CardDescription>
                  {canConnect
                    ? `Connect for ${clientName(connectClientId || null)}`
                    : 'Set this platform’s app credentials on the server to enable it.'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  size="sm"
                  disabled={!canConnect}
                  loading={startConnect.isPending && startConnect.variables === platform}
                  onClick={() => {
                    setParams({});
                    startConnect.mutate(platform);
                  }}
                >
                  Connect
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Existing connections, one row per credential, labeled by client. */}
      <div>
        <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
          Connected accounts ({allCreds.length})
        </h2>
        {allCreds.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No accounts connected yet.</p>
        ) : (
          <div className="divide-y divide-slate-200 rounded-lg border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
            {allCreds.map((cred) => (
              <div key={cred.id} className="flex flex-wrap items-start justify-between gap-3 p-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {PLATFORM_LABELS[cred.platform] ?? cred.platform}
                    </span>
                    <Badge variant={cred.client_id ? 'info' : 'secondary'}>
                      {clientName(cred.client_id)}
                    </Badge>
                    {!cred.is_active && <Badge variant="default">Inactive</Badge>}
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    {cred.display_name ?? 'Account connected'}
                  </p>
                  <div className="mt-2">
                    <AccountRef cred={cred} />
                  </div>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  loading={remove.isPending && remove.variables === cred.id}
                  onClick={() => remove.mutate(cred.id)}
                >
                  Disconnect
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Some platforms publish to a specific target (Facebook Page id, Instagram
 * business user id, LinkedIn org id). Let the operator set it post-connect.
 */
function AccountRef({ cred }: { cred: PlatformCredential }) {
  const qc = useQueryClient();
  const [value, setValue] = useState(cred.account_ref ?? '');
  const save = useMutation({
    mutationFn: () => distributionApi.patchCredential(cred.id, { account_ref: value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['credentials'] }),
  });
  const needsRef = ['facebook', 'instagram'].includes(cred.platform);
  if (!needsRef) return null;
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-slate-600 dark:text-slate-400">
        {cred.platform === 'facebook' ? 'Page id' : 'IG business account id'}
      </label>
      <div className="flex gap-2">
        <Input value={value} onChange={(e) => setValue(e.target.value)} placeholder="required to publish" />
        <Button size="sm" variant="secondary" loading={save.isPending} onClick={() => save.mutate()}>
          Save
        </Button>
      </div>
    </div>
  );
}
