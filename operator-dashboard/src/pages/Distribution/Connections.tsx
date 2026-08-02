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
import { getApiErrorMessage } from '@/utils/apiError';

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  twitter: 'Twitter / X',
  facebook: 'Facebook',
  instagram: 'Instagram',
  tiktok: 'TikTok',
  youtube: 'YouTube',
  bluesky: 'Bluesky',
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
  // The credential (if any) for a given platform under the CURRENTLY selected client scope
  // (account-level creds have client_id null). save_credential is an UPSERT that reuses the
  // row and reactivates is_active, so re-running OAuth is the intended refresh/reconnect
  // path — we relabel to "Reconnect" rather than blocking it.
  const scopeCredFor = (platform: string) =>
    allCreds.find((c) => c.platform === platform && (c.client_id ?? '') === connectClientId);

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
          // Existing credential for the currently selected client scope, if any.
          const scopeCred = scopeCredFor(platform);
          const active = scopeCred?.is_active ?? false;
          return (
            <Card key={platform}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{PLATFORM_LABELS[platform] ?? platform}</CardTitle>
                  <Badge
                    variant={
                      scopeCred
                        ? active
                          ? 'success'
                          : 'default'
                        : canConnect
                          ? 'secondary'
                          : 'default'
                    }
                  >
                    {scopeCred
                      ? active
                        ? 'Connected'
                        : 'Inactive'
                      : canConnect
                        ? 'Available'
                        : 'Not configured'}
                  </Badge>
                </div>
                <CardDescription>
                  {!canConnect
                    ? 'Set this platform’s app credentials on the server to enable it.'
                    : scopeCred
                      ? active
                        ? `${clientName(connectClientId || null)} is connected — re-auth to refresh the token.`
                        : `${clientName(connectClientId || null)} is inactive — reconnect to restore it.`
                      : `Connect for ${clientName(connectClientId || null)}`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* Reconnect is a safe upsert (reuses the row + reactivates) — never blocked,
                    so an expired/revoked credential can always be recovered from here. */}
                <Button
                  size="sm"
                  disabled={!canConnect}
                  loading={startConnect.isPending && startConnect.variables === platform}
                  onClick={() => {
                    setParams({});
                    startConnect.mutate(platform);
                  }}
                >
                  {scopeCred ? 'Reconnect' : 'Connect'}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Bluesky uses AT Protocol app-password auth (no OAuth), so it's connected here
          via the manual credential API rather than the OAuth grid above. */}
      <BlueskyConnect clientId={connectClientId} clientLabel={clientName(connectClientId || null)} />

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

/**
 * Bluesky (AT Protocol) authenticates with a handle + app password, not OAuth, so it
 * can't use the OAuth connect grid. Store the app password as the credential's access
 * token and the handle as its account_ref, scoped to the currently selected client.
 * save_credential is an upsert, so re-submitting rotates the app password for that scope.
 */
function BlueskyConnect({ clientId, clientLabel }: { clientId: string; clientLabel: string }) {
  const qc = useQueryClient();
  const [handle, setHandle] = useState('');
  const [appPassword, setAppPassword] = useState('');

  const connect = useMutation({
    mutationFn: () =>
      distributionApi.connect({
        platform: 'bluesky',
        access_token: appPassword.trim(),
        account_ref: handle.trim(),
        // Store the handle as the display name so the credential is identifiable in the
        // list (which renders display_name); account_ref carries the same handle for the
        // publisher. The backend verifies the app password before persisting.
        display_name: handle.trim(),
        client_id: clientId || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['credentials'] });
      setHandle('');
      setAppPassword('');
    },
  });

  // Handle + app password are both required; the app password must be an app-specific
  // password (Settings → App passwords in Bluesky), never the account password.
  const canSubmit = handle.trim().length > 0 && appPassword.trim().length > 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{PLATFORM_LABELS.bluesky}</CardTitle>
          <Badge variant="secondary">App password</Badge>
        </div>
        <CardDescription>
          Connect for {clientLabel}. Bluesky uses an app password, not OAuth — create one in
          Bluesky under Settings → App passwords, then paste your handle and that password here.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <div className="space-y-1">
            <label htmlFor="bsky-handle" className="text-xs font-medium text-slate-600 dark:text-slate-400">
              Handle
            </label>
            <Input
              id="bsky-handle"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              placeholder="you.bsky.social"
              autoComplete="off"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="bsky-app-pw" className="text-xs font-medium text-slate-600 dark:text-slate-400">
              App password
            </label>
            <Input
              id="bsky-app-pw"
              type="password"
              value={appPassword}
              onChange={(e) => setAppPassword(e.target.value)}
              placeholder="xxxx-xxxx-xxxx-xxxx"
              autoComplete="off"
            />
          </div>
          <Button
            size="sm"
            disabled={!canSubmit}
            loading={connect.isPending}
            onClick={() => connect.mutate()}
          >
            Connect
          </Button>
        </div>
        {connect.isError && (
          <p className="mt-2 text-xs text-red-600 dark:text-red-400">
            {getApiErrorMessage(
              connect.error,
              'Couldn’t connect — check the handle and app password and try again.',
            )}
          </p>
        )}
        {connect.isSuccess && (
          <p className="mt-2 text-xs text-green-600 dark:text-green-400">
            Bluesky connected for {clientLabel}.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
