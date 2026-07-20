import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { distributionApi, PlatformCredential } from '@/api/distribution';

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

  const startConnect = useMutation({
    mutationFn: (platform: string) => distributionApi.oauthStart(platform),
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
  const credByPlatform = new Map<string, PlatformCredential>();
  (creds.data ?? []).forEach((c) => credByPlatform.set(c.platform, c));

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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {platforms.map((platform) => {
          const cred = credByPlatform.get(platform);
          const canConnect = configured.has(platform);
          return (
            <Card key={platform}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{PLATFORM_LABELS[platform] ?? platform}</CardTitle>
                  {cred ? (
                    <Badge variant="success">Connected</Badge>
                  ) : canConnect ? (
                    <Badge variant="secondary">Available</Badge>
                  ) : (
                    <Badge variant="default">Not configured</Badge>
                  )}
                </div>
                <CardDescription>
                  {cred
                    ? cred.display_name ?? 'Account connected'
                    : canConnect
                      ? 'Ready to connect'
                      : 'Set this platform’s app credentials on the server to enable it.'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {cred ? (
                  <>
                    <AccountRef cred={cred} />
                    <Button
                      variant="danger"
                      size="sm"
                      loading={remove.isPending}
                      onClick={() => remove.mutate(cred.id)}
                    >
                      Disconnect
                    </Button>
                  </>
                ) : (
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
                )}
              </CardContent>
            </Card>
          );
        })}
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
