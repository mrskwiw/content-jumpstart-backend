import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { WizardStepper } from '@/components/wizard/WizardStepper';
import { ClientProfilePanel } from '@/components/wizard/ClientProfilePanel';
import { ResearchPanel } from '@/components/wizard/ResearchPanel';
import { TemplateSelectionPanel } from '@/components/wizard/TemplateSelectionPanel';
import { GenerationPanel } from '@/components/wizard/GenerationPanel';
import { QualityGatePanel } from '@/components/wizard/QualityGatePanel';
import { ExportPanel } from '@/components/wizard/ExportPanel';
import { postsApi } from '@/api/posts';
import { runsApi } from '@/api/runs';
import { projectsApi } from '@/api/projects';
import { clientsApi } from '@/api/clients';
import type { ClientBrief, PostDraft } from '@/types/domain';
import type { CreateProjectInput } from '@/api/projects';
import type { PaginatedResponse } from '@/types/pagination';
import { Button, Card, CardContent, Select } from '@/components/ui';

type StepKey = 'profile' | 'research' | 'templates' | 'generate' | 'quality' | 'export';

const steps: { key: StepKey; label: string }[] = [
  { key: 'profile', label: 'Client Profile' },
  { key: 'research', label: 'Research' },
  { key: 'templates', label: 'Templates' },
  { key: 'generate', label: 'Generate' },
  { key: 'quality', label: 'Quality Gate' },
  { key: 'export', label: 'Export' },
];

export default function Wizard() {
  const location = useLocation();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [projectId, setProjectId] = useState<string | null>(
    (location.state as { projectId?: string })?.projectId || null
  );
  const [clientId, setClientId] = useState<string | null>(
    (location.state as { clientId?: string })?.clientId || null
  );

  const [activeStep, setActiveStep] = useState<StepKey>('profile');
  const [clientBrief, setClientBrief] = useState<ClientBrief | null>(null);
  const [selectedTemplates, setSelectedTemplates] = useState<number[]>([]);
  const [isCreatingNewClient, setIsCreatingNewClient] = useState<boolean>(true);

  // Query to list existing clients
  const { data: existingClients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  // Mutation to create client
  const createClientMutation = useMutation({
    mutationFn: (data: { name: string; email?: string }) => clientsApi.create(data),
    onSuccess: (data) => {
      setClientId(data.id);
      qc.invalidateQueries({ queryKey: ['clients'] });
    },
  });

  // Mutation to create project
  const createProjectMutation = useMutation({
    mutationFn: (data: CreateProjectInput) => projectsApi.create(data),
    onSuccess: (data) => {
      setProjectId(data.id);
      qc.invalidateQueries({ queryKey: ['project', data.id] });
    },
  });

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const { data: runs } = useQuery({
    queryKey: ['runs', { projectId }],
    queryFn: () => runsApi.list({ projectId: projectId! }),
    enabled: !!projectId,
  });

  const { data: postsResponse, refetch: refetchPosts } = useQuery<PaginatedResponse<PostDraft>>({
    queryKey: ['posts', { projectId }],
    queryFn: () => postsApi.list({ projectId: projectId! }),
    enabled: !!projectId,
  });

  // Extract posts from paginated response (Week 3 optimization)
  const posts = postsResponse?.items ?? [];
  const flagged = posts.filter((p) => p.status === 'flagged' || (p.flags && p.flags.length > 0));

  // Handler for saving client profile
  const handleSaveProfile = async (brief: ClientBrief) => {
    try {
      let finalClientId = clientId;

      // Create client if creating new, otherwise use existing clientId
      if (isCreatingNewClient) {
        const client = await createClientMutation.mutateAsync({
          name: brief.companyName,
          email: undefined, // Can be added to form later
        });
        finalClientId = client.id;
      } else if (!clientId) {
        alert('Please select an existing client or create a new one.');
        return;
      }

      // Create project for this client
      if (!finalClientId) {
        alert('Please select an existing client or create a new one.');
        return;
      }

      const projectInput: CreateProjectInput = {
        name: `${brief.companyName} - Content Project`,
        clientId: finalClientId,
        platforms: brief.platforms ?? [],
        templates: selectedTemplates.map(String),
        tone: brief.tonePreference ?? undefined,
      };

      await createProjectMutation.mutateAsync(projectInput);

      // Save brief locally
      setClientBrief(brief);

      // Move to next step
      setActiveStep('research');
    } catch (error) {
      console.error('Failed to create project:', error);
      alert('Failed to create project. Please try again.');
    }
  };

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">Project Wizard</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Multi-step flow for client profile → templates → generation → quality gate → export.
        </p>
      </header>

      <WizardStepper steps={steps} active={activeStep} onChange={(k) => setActiveStep(k as StepKey)} />

      {activeStep === 'profile' && (
        <div className="space-y-4">
          {/* Client Selection */}
          <Card>
            <CardContent className="p-6">
              <h3 className="mb-4 text-lg font-semibold text-neutral-900 dark:text-neutral-100">Select Client</h3>

              {/* Toggle between new and existing */}
              <div className="mb-4 flex gap-2">
                <Button
                  variant={isCreatingNewClient ? 'primary' : 'secondary'}
                  onClick={() => setIsCreatingNewClient(true)}
                >
                  Create New Client
                </Button>
                <Button
                  variant={!isCreatingNewClient ? 'primary' : 'secondary'}
                  onClick={() => setIsCreatingNewClient(false)}
                >
                  Use Existing Client
                </Button>
              </div>

              {/* Existing client selector */}
              {!isCreatingNewClient && (
                <Select
                  label="Select Existing Client"
                  value={clientId || ''}
                  onChange={(e) => setClientId(e.target.value || null)}
                  helperText={!clientId ? "Select an existing client to continue" : undefined}
                >
                  <option value="">-- Select a client --</option>
                  {(existingClients || []).map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </Select>
              )}

              {/* New client info */}
              {isCreatingNewClient && (
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  A new client will be created from the company name in the profile below.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Client Profile Form */}
          <ClientProfilePanel
            projectId={projectId || undefined}
            initialData={clientBrief || undefined}
            onSave={handleSaveProfile}
          />
        </div>
      )}

      {activeStep === 'research' && projectId && clientId && (
        <ResearchPanel
          projectId={projectId}
          clientId={clientId}
          onContinue={() => setActiveStep('templates')}
        />
      )}

      {activeStep === 'templates' && (
        <TemplateSelectionPanel
          initialSelection={selectedTemplates}
          onContinue={(templateIds) => {
            setSelectedTemplates(templateIds);
            setActiveStep('generate');
          }}
        />
      )}

      {activeStep === 'generate' && projectId && clientId && (
        <div className="grid gap-4 lg:grid-cols-2">
          <GenerationPanel
            projectId={projectId}
            clientId={clientId}
            onStarted={() => {
              qc.invalidateQueries({ queryKey: ['runs', { projectId }] });
              refetchPosts();
              setActiveStep('quality');
            }}
          />
          <QualityGatePanel
            posts={posts ?? []}
            projectId={projectId}
            onRegenerated={() => {
              refetchPosts();
            }}
          />
        </div>
      )}

      {activeStep === 'quality' && projectId && (
        <div className="space-y-4">
          <QualityGatePanel
            posts={posts ?? []}
            projectId={projectId}
            onRegenerated={() => {
              refetchPosts();
            }}
          />
          <div className="flex justify-end">
            <button
              onClick={() => setActiveStep('export')}
              disabled={flagged.length > 0}
              className="rounded-md bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {flagged.length > 0 ? `${flagged.length} posts flagged - fix before exporting` : 'Continue to Export'}
            </button>
          </div>
        </div>
      )}

      {activeStep === 'export' && projectId && clientId && (
        <ExportPanel
          projectId={projectId}
          clientId={clientId}
          onExported={() => {
            qc.invalidateQueries({ queryKey: ['deliverables'] });
          }}
        />
      )}

      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Wizard Status</h3>
        <div className="mt-2 space-y-1">
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Project:</strong> {project?.name || projectId || 'Not created'}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Client Brief:</strong> {clientBrief ? '✓ Saved' : 'Not set'}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Templates:</strong> {selectedTemplates.length > 0 ? `${selectedTemplates.length} selected` : 'None selected'}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Posts:</strong> {posts?.length ?? 0} generated
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Flagged:</strong> {flagged.length}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Runs:</strong> {runs?.length ?? 0}
          </p>
        </div>
      </div>
    </div>
  );
}
