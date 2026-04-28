import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { ClientProfilePanel } from '@/components/wizard/ClientProfilePanel';
import { clientsApi } from '@/api';
import type { ApiError } from '@/types/api-types';
import { type ClientBrief } from '@/types/domain';

export default function NewClient() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createClientMutation = useMutation({
    mutationFn: async (clientData: ClientBrief) => {
      const client = await clientsApi.create({
        name: clientData.companyName,
        email: '', // Optional field
        businessDescription: clientData.businessDescription,
        idealCustomer: clientData.idealCustomer,
        mainProblemSolved: clientData.mainProblemSolved,
        tonePreference: clientData.tonePreference,
        platforms: clientData.platforms,
        customerPainPoints: clientData.customerPainPoints,
        customerQuestions: clientData.customerQuestions,
        industry: clientData.industry,
        keywords: clientData.keywords,
        competitors: clientData.competitors,
        location: clientData.location,
        // Extended profile fields (auto-population data sources)
        founderName: clientData.founderName,
        brandPersonality: clientData.brandPersonality,
        toneToAvoid: clientData.toneToAvoid,
        dataUsage: clientData.dataUsage,
        stories: clientData.stories,
        misconceptions: clientData.misconceptions,
        measurableResults: clientData.measurableResults,
        postingFrequency: clientData.postingFrequency,
        mainCta: clientData.mainCta,
        keyPhrases: clientData.keyPhrases,
      });
      return client;
    },
    onSuccess: (client) => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      navigate(`/dashboard/clients/${client.id}`);
    },
    onError: (error: unknown) => {
      console.error('Failed to create client:', error);
      alert((error as Error)?.message || 'Failed to create client. Please try again.');
    },
  });

  const handleSave = async (clientData: ClientBrief) => {
    await createClientMutation.mutateAsync(clientData);
  };

  const handleCancel = () => {
    navigate('/dashboard/clients');
  };

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <div className="container max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={handleCancel}
            className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 mb-4 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Clients
          </button>
          <div>
            <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100">
              Create New Client
            </h1>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              Add a new client to your portfolio with comprehensive profile information
            </p>
          </div>
        </div>

        {/* Client Profile Form */}
        <div className="bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 shadow-sm">
          <ClientProfilePanel
            initialData={{}}
            onSave={handleSave}
          />
        </div>

        {/* Action Buttons - Footer */}
        <div className="mt-6 flex items-center justify-end gap-3 pb-8">
          <button
            type="button"
            onClick={handleCancel}
            disabled={createClientMutation.isPending}
            className="px-6 py-2.5 text-sm font-medium text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Cancel
          </button>
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            Use the "Save Client Profile" button in the form above to create the client
          </div>
        </div>
      </div>
    </div>
  );
}
