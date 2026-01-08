import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { WizardStepper } from '@/components/wizard/WizardStepper';
import { ClientProfilePanel } from '@/components/wizard/ClientProfilePanel';
import { ResearchPanel } from '@/components/wizard/ResearchPanel';
import { TemplateSelectionPanel } from '@/components/wizard/TemplateSelectionPanel';
import { TemplateQuantitySelector } from '@/components/wizard/TemplateQuantitySelector';
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
import { Button, Card, CardContent, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui';

type StepKey = 'profile' | 'research' | 'templates' | 'quality' | 'export';

const steps: { key: StepKey; label: string }[] = [
  { key: 'profile', label: 'Client Profile' },
  { key: 'research', label: 'Research' },
  { key: 'templates', label: 'Templates' },
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
  const [maxReachedStep, setMaxReachedStep] = useState<StepKey>('profile');
  const [clientBrief, setClientBrief] = useState<ClientBrief | null>(null);
  const [selectedTemplates, setSelectedTemplates] = useState<number[]>([]);
  const [isCreatingNewClient, setIsCreatingNewClient] = useState<boolean>(true);

  // Template quantities state (new pricing model)
  const [templateQuantities, setTemplateQuantities] = useState<Record<number, number>>({});
  const [includeResearch, setIncludeResearch] = useState<boolean>(false);
  const [totalPrice, setTotalPrice] = useState<number>(0);
  const [customTopics, setCustomTopics] = useState<string[]>([]);  // NEW: topic override for generation

  // Query to list existing clients
  const { data: existingClients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  // Query to fetch selected client's data
  const { data: selectedClient } = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => clientsApi.get(clientId!),
    enabled: !!clientId && !isCreatingNewClient,
  });

  // Mutation to create client
  const createClientMutation = useMutation({
    mutationFn: (data: any) => clientsApi.create(data),
    onSuccess: (data) => {
      setClientId(data.id);
      qc.invalidateQueries({ queryKey: ['clients'] });
      console.log(`✅ Client created successfully: ${data.id} (${data.name})`);
    },
    onError: (error: any) => {
      console.error('❌ Client creation failed:', error);
      console.error('Error details:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
      });
    },
  });

  // Mutation to update client
  const updateClientMutation = useMutation({
    mutationFn: (data: { id: string } & any) => {
      const { id, ...updateData } = data;
      return clientsApi.update(id, updateData);
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['clients'] });
      qc.invalidateQueries({ queryKey: ['client', clientId] });
      console.log(`✅ Client updated successfully: ${data.id} (${data.name})`);
    },
    onError: (error: any) => {
      console.error('❌ Client update failed:', error);
      console.error('Error details:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
      });
    },
  });

  // Mutation to create project
  const createProjectMutation = useMutation({
    mutationFn: (data: CreateProjectInput) => projectsApi.create(data),
    onSuccess: (data) => {
      setProjectId(data.id);
      qc.invalidateQueries({ queryKey: ['project', data.id] });
      console.log(`✅ Project created successfully: ${data.id} (${data.name})`);
    },
    onError: (error: any) => {
      console.error('❌ Project creation failed:', error);
      console.error('Error details:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
      });
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

  // Populate form with selected client's data when loading existing client
  useEffect(() => {
    if (selectedClient && !isCreatingNewClient) {
      // SECURITY FIX: Check if update is needed to prevent unnecessary re-renders (TR-017)
      const needsUpdate =
        clientBrief?.companyName !== selectedClient.name ||
        clientBrief?.businessDescription !== (selectedClient.businessDescription || '') ||
        clientBrief?.idealCustomer !== (selectedClient.idealCustomer || '');

      if (needsUpdate) {
        setClientBrief({
          companyName: selectedClient.name,
          businessDescription: selectedClient.businessDescription || '',
          idealCustomer: selectedClient.idealCustomer || '',
          mainProblemSolved: selectedClient.mainProblemSolved || '',
          tonePreference: selectedClient.tonePreference || 'professional',
          platforms: selectedClient.platforms || [],
          customerPainPoints: selectedClient.customerPainPoints || [],
          customerQuestions: selectedClient.customerQuestions || [],
        });
      }
    }
  }, [selectedClient, isCreatingNewClient, clientBrief]);

  // Helper to advance to a step (updates maxReachedStep if moving forward)
  const advanceToStep = (targetStep: StepKey) => {
    const stepIndex = (key: StepKey) => steps.findIndex(s => s.key === key);
    const targetIndex = stepIndex(targetStep);
    const maxIndex = stepIndex(maxReachedStep);

    // Update maxReachedStep if we're advancing to a new step
    if (targetIndex > maxIndex) {
      setMaxReachedStep(targetStep);
    }

    setActiveStep(targetStep);
  };

  // Handler for stepper clicks - only allow navigation to reached steps
  const handleStepperClick = (targetStep: StepKey) => {
    const stepIndex = (key: StepKey) => steps.findIndex(s => s.key === key);
    const targetIndex = stepIndex(targetStep);
    const maxIndex = stepIndex(maxReachedStep);

    // Only allow clicking on steps we've already reached
    if (targetIndex <= maxIndex) {
      setActiveStep(targetStep);
    }
  };

  // Handler for saving client profile
  const handleSaveProfile = async (brief: ClientBrief) => {
    console.log('📝 Starting client profile save...', {
      isCreatingNew: isCreatingNewClient,
      existingClientId: clientId,
      companyName: brief.companyName,
    });

    try {
      let finalClientId = clientId;

      // Step 1: Create or update client
      if (isCreatingNewClient) {
        console.log('🆕 Creating new client...');
        try {
          const client = await createClientMutation.mutateAsync({
            name: brief.companyName,
            email: undefined, // Can be added to form later
            businessDescription: brief.businessDescription,
            idealCustomer: brief.idealCustomer,
            mainProblemSolved: brief.mainProblemSolved,
            tonePreference: brief.tonePreference,
            platforms: brief.platforms,
            customerPainPoints: brief.customerPainPoints,
            customerQuestions: brief.customerQuestions,
          });
          finalClientId = client.id;
          console.log('✅ Client created:', finalClientId);
        } catch (error: any) {
          console.error('❌ Client creation failed:', error);
          const errorMsg = error?.response?.data?.detail || error?.message || 'Unknown error';
          alert(`Failed to create client: ${errorMsg}\n\nPlease check the console for details and try again.`);
          return; // Stop here - don't try to create project
        }
      } else if (!clientId) {
        alert('Please select an existing client or create a new one.');
        return;
      } else {
        console.log('🔄 Updating existing client...', clientId);
        try {
          // Always update existing client with all fields from the form
          await updateClientMutation.mutateAsync({
            id: clientId,
            name: brief.companyName,
            businessDescription: brief.businessDescription,
            idealCustomer: brief.idealCustomer,
            mainProblemSolved: brief.mainProblemSolved,
            tonePreference: brief.tonePreference,
            platforms: brief.platforms,
            customerPainPoints: brief.customerPainPoints,
            customerQuestions: brief.customerQuestions,
          });
          finalClientId = clientId;
          console.log('✅ Client updated:', finalClientId);
        } catch (error: any) {
          console.error('❌ Client update failed:', error);
          const errorMsg = error?.response?.data?.detail || error?.message || 'Unknown error';
          alert(`Failed to update client: ${errorMsg}\n\nPlease check the console for details and try again.`);
          return; // Stop here - don't try to create project
        }
      }

      // Step 2: Create project for this client
      if (!finalClientId) {
        alert('Client ID is missing. Please try again.');
        return;
      }

      console.log('📋 Creating project for client...', finalClientId);
      const projectInput: CreateProjectInput = {
        name: `${brief.companyName} - Content Project`,
        clientId: finalClientId,
        platforms: brief.platforms ?? [],
        templates: selectedTemplates.map(String), // Legacy field for backward compatibility
        templateQuantities: templateQuantities, // New field for per-template quantities
        pricePerPost: includeResearch ? 55.0 : 40.0, // $40 base + $15 research
        researchPricePerPost: includeResearch ? 15.0 : 0.0,
        totalPrice: totalPrice,
        tone: brief.tonePreference ?? undefined,
      };

      try {
        await createProjectMutation.mutateAsync(projectInput);
        console.log('✅ Project created successfully');
      } catch (error: any) {
        console.error('❌ Project creation failed:', error);
        const errorMsg = error?.response?.data?.detail || error?.message || 'Unknown error';
        alert(`Client saved successfully, but project creation failed: ${errorMsg}\n\nThe client has been saved. You can try creating the project again from the client detail page.`);
        return; // Stop here - client is saved but project failed
      }

      // Save brief locally
      setClientBrief(brief);

      // Move to next step
      console.log('✅ All save operations successful, advancing to research step');
      advanceToStep('research');
    } catch (error: any) {
      // This catch should rarely be hit since we have specific catches above
      console.error('❌ Unexpected error in handleSaveProfile:', error);
      alert(`An unexpected error occurred: ${error?.message || 'Unknown error'}\n\nPlease check the console for details.`);
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

      <WizardStepper
        steps={steps}
        active={activeStep}
        maxReached={maxReachedStep}
        onChange={(k) => handleStepperClick(k as StepKey)}
      />

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
                  onClick={() => {
                    setIsCreatingNewClient(true);
                    setClientId(null);
                    setClientBrief(null);
                  }}
                >
                  Create New Client
                </Button>
                <Button
                  variant={!isCreatingNewClient ? 'primary' : 'secondary'}
                  onClick={() => {
                    setIsCreatingNewClient(false);
                    setClientBrief(null);
                  }}
                >
                  Use Existing Client
                </Button>
              </div>

              {/* Existing client selector */}
              {!isCreatingNewClient && (
                <div>
                  <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                    Select Existing Client
                  </label>
                  <Select value={clientId || ''} onValueChange={(value) => setClientId(value || null)}>
                    <SelectTrigger>
                      <SelectValue placeholder="-- Select a client --" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">-- Select a client --</SelectItem>
                      {(existingClients || []).map((client) => (
                        <SelectItem key={client.id} value={client.id}>
                          {client.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {!clientId && (
                    <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                      Select an existing client to continue
                    </p>
                  )}
                </div>
              )}

              {/* New client info */}
              {isCreatingNewClient && (
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  A new client will be created from the company name in the profile below.
                </p>
              )}

              {/* Continue button for existing client selection */}
              {!isCreatingNewClient && clientId && (
                <div className="mt-4 flex justify-end border-t border-neutral-200 dark:border-neutral-700 pt-4">
                  <Button
                    variant="primary"
                    onClick={() => {
                      // Validate client has required data before proceeding
                      const businessDesc = selectedClient?.businessDescription || '';
                      const targetAudience = selectedClient?.idealCustomer || '';

                      if (businessDesc.length < 70) {
                        alert('Client profile incomplete: Business description must be at least 70 characters (required for research tools). Please complete the client profile below before continuing.');
                        return;
                      }

                      if (targetAudience.length < 20) {
                        alert('Client profile incomplete: Target audience description must be at least 20 characters (required for research tools). Please complete the client profile below before continuing.');
                        return;
                      }

                      // Create project with minimal info for existing client
                      const projectInput: CreateProjectInput = {
                        name: `${selectedClient?.name || 'Client'} - Content Project`,
                        clientId: clientId,
                        platforms: [],
                        templates: [], // Legacy field
                        templateQuantities: {}, // Will be set in template selection step
                        pricePerPost: 40.0,
                        researchPricePerPost: 0.0,
                        totalPrice: 0.0,
                        tone: 'professional',
                      };
                      createProjectMutation.mutate(projectInput, {
                        onSuccess: () => {
                          advanceToStep('research');
                        },
                      });
                    }}
                  >
                    Continue to Research
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Client Profile Form - Only show when creating new OR existing client selected */}
          {(isCreatingNewClient || (!isCreatingNewClient && clientId)) && (
            <ClientProfilePanel
              projectId={projectId || undefined}
              initialData={clientBrief || undefined}
              onSave={handleSaveProfile}
            />
          )}
        </div>
      )}

      {activeStep === 'research' && projectId && clientId && (
        <ResearchPanel
          projectId={projectId}
          clientId={clientId}
          onContinue={() => advanceToStep('templates')}
        />
      )}

      {activeStep === 'templates' && (
        <div className="space-y-4">
          {/* Template Selection */}
          <Card>
            <CardContent className="p-6">
              <TemplateQuantitySelector
                initialQuantities={templateQuantities}
                initialIncludeResearch={includeResearch}
                initialTopics={customTopics}
                onContinue={(quantities, research, price, topics) => {
                  setTemplateQuantities(quantities);
                  setIncludeResearch(research);
                  setTotalPrice(price);
                  setCustomTopics(topics);
                  advanceToStep('quality');
                }}
              />
            </CardContent>
          </Card>
        </div>
      )}

      {activeStep === 'quality' && projectId && clientId && (
        <div className="space-y-4">
          {/* Show GenerationPanel if no posts exist, otherwise show Quality view */}
          {(!posts || posts.length === 0) ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <GenerationPanel
                projectId={projectId}
                clientId={clientId}
                templateQuantities={templateQuantities}
                customTopics={customTopics}
                onStarted={() => {
                  qc.invalidateQueries({ queryKey: ['runs', { projectId }] });
                  refetchPosts();
                }}
              />
              <Card>
                <CardContent className="p-6">
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                    Quality Gate Preview
                  </h3>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    Generate posts to see quality analysis and validation results here.
                  </p>
                </CardContent>
              </Card>
            </div>
          ) : (
            <>
              <QualityGatePanel
                posts={posts}
                projectId={projectId}
                onRegenerated={() => {
                  refetchPosts();
                }}
              />
              <div className="flex justify-end">
                <button
                  onClick={() => advanceToStep('export')}
                  disabled={flagged.length > 0}
                  className="rounded-md bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {flagged.length > 0 ? `${flagged.length} posts flagged - fix before exporting` : 'Continue to Export'}
                </button>
              </div>
            </>
          )}
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
            <strong>Templates:</strong> {Object.keys(templateQuantities).length > 0 ? `${Object.keys(templateQuantities).length} selected` : 'Not selected'}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Total Posts:</strong> {Object.values(templateQuantities).reduce((sum, qty) => sum + qty, 0) || 0}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Research:</strong> {includeResearch ? 'Yes (+$15/post)' : 'No'}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Total Price:</strong> {totalPrice > 0 ? `$${totalPrice.toLocaleString()}` : 'Not calculated'}
          </p>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            <strong>Generated:</strong> {posts?.length ?? 0} posts
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
