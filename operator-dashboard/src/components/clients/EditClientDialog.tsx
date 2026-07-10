import { useState, useEffect } from 'react';
import { X, Loader2, User, Save } from 'lucide-react';
import type { Client } from '@/types/domain';
import type { UpdateClientInput } from '@/api/clients';

interface EditClientDialogProps {
  client: Client;
  open: boolean;
  onClose: () => void;
  onSubmit: (updates: UpdateClientInput) => void;
  isSubmitting?: boolean;
}

export function EditClientDialog({
  client,
  open,
  onClose,
  onSubmit,
  isSubmitting = false,
}: EditClientDialogProps) {
  const [name, setName] = useState(client.name);
  const [email, setEmail] = useState(client.email ?? '');
  const [industry, setIndustry] = useState(client.industry ?? '');
  const [location, setLocation] = useState(client.location ?? '');
  const [businessDescription, setBusinessDescription] = useState(client.businessDescription ?? '');
  const [idealCustomer, setIdealCustomer] = useState(client.idealCustomer ?? '');
  const [mainProblemSolved, setMainProblemSolved] = useState(client.mainProblemSolved ?? '');
  const [tonePreference, setTonePreference] = useState(client.tonePreference ?? '');
  const [platforms, setPlatforms] = useState<string[]>(client.platforms ?? []);
  const [keywords, setKeywords] = useState<string[]>(client.keywords ?? []);
  const [competitors, setCompetitors] = useState<string[]>(client.competitors ?? []);
  const [customerPainPoints, setCustomerPainPoints] = useState<string[]>(client.customerPainPoints ?? []);
  const [customerQuestions, setCustomerQuestions] = useState<string[]>(client.customerQuestions ?? []);

  // Re-sync the controlled form fields when a different `client` is passed in
  // (this dialog instance is reused across clients). Effect-based sync is the
  // established pattern here; deps are complete (the whole `client` object).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional prop->state sync on entity change
    setName(client.name);
    setEmail(client.email ?? '');
    setIndustry(client.industry ?? '');
    setLocation(client.location ?? '');
    setBusinessDescription(client.businessDescription ?? '');
    setIdealCustomer(client.idealCustomer ?? '');
    setMainProblemSolved(client.mainProblemSolved ?? '');
    setTonePreference(client.tonePreference ?? '');
    setPlatforms(client.platforms ?? []);
    setKeywords(client.keywords ?? []);
    setCompetitors(client.competitors ?? []);
    setCustomerPainPoints(client.customerPainPoints ?? []);
    setCustomerQuestions(client.customerQuestions ?? []);
  }, [client]);

  const handleSubmit = () => {
    const updates: UpdateClientInput = {};
    if (name !== client.name) updates.name = name;
    if (email !== (client.email ?? '')) updates.email = email || undefined;
    if (industry !== (client.industry ?? '')) updates.industry = industry || undefined;
    if (location !== (client.location ?? '')) updates.location = location || undefined;
    if (businessDescription !== (client.businessDescription ?? '')) updates.businessDescription = businessDescription || undefined;
    if (idealCustomer !== (client.idealCustomer ?? '')) updates.idealCustomer = idealCustomer || undefined;
    if (mainProblemSolved !== (client.mainProblemSolved ?? '')) updates.mainProblemSolved = mainProblemSolved || undefined;
    if (tonePreference !== (client.tonePreference ?? '')) updates.tonePreference = tonePreference || undefined;
    if (JSON.stringify(platforms) !== JSON.stringify(client.platforms ?? [])) {
      updates.platforms = platforms.length > 0 ? platforms as UpdateClientInput['platforms'] : undefined;
    }
    if (JSON.stringify(keywords) !== JSON.stringify(client.keywords ?? [])) {
      updates.keywords = keywords.length > 0 ? keywords : undefined;
    }
    if (JSON.stringify(competitors) !== JSON.stringify(client.competitors ?? [])) {
      updates.competitors = competitors.length > 0 ? competitors : undefined;
    }
    if (JSON.stringify(customerPainPoints) !== JSON.stringify(client.customerPainPoints ?? [])) {
      updates.customerPainPoints = customerPainPoints.length > 0 ? customerPainPoints : undefined;
    }
    if (JSON.stringify(customerQuestions) !== JSON.stringify(client.customerQuestions ?? [])) {
      updates.customerQuestions = customerQuestions.length > 0 ? customerQuestions : undefined;
    }
    onSubmit(updates);
  };

  const handleCancel = () => {
    setName(client.name);
    setEmail(client.email ?? '');
    setIndustry(client.industry ?? '');
    setLocation(client.location ?? '');
    setBusinessDescription(client.businessDescription ?? '');
    setIdealCustomer(client.idealCustomer ?? '');
    setMainProblemSolved(client.mainProblemSolved ?? '');
    setTonePreference(client.tonePreference ?? '');
    setPlatforms(client.platforms ?? []);
    setKeywords(client.keywords ?? []);
    setCompetitors(client.competitors ?? []);
    setCustomerPainPoints(client.customerPainPoints ?? []);
    setCustomerQuestions(client.customerQuestions ?? []);
    onClose();
  };

  const handleArrayInput = (value: string, setter: (arr: string[]) => void) => {
    const arr = value.split(',').map(s => s.trim()).filter(s => s.length > 0);
    setter(arr);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black/50 transition-opacity" onClick={handleCancel} />
      <div className="absolute inset-y-0 right-0 flex max-w-full pl-10">
        <div className="w-screen max-w-2xl">
          <div className="flex h-full flex-col overflow-y-scroll bg-white dark:bg-neutral-900 shadow-xl">
            <div className="border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 px-6 py-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/20">
                    <User className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Edit Client</h2>
                    <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">Update client information and profile details</p>
                  </div>
                </div>
                <button onClick={handleCancel} className="rounded-lg p-2 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300">
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wide">Basic Information</h3>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Company Name <span className="text-red-500">*</span></label>
                  <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Company name" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="contact@company.com" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Industry</label>
                  <input type="text" value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="e.g., SaaS, Healthcare, Finance" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Location</label>
                  <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g., San Francisco, CA" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
              </div>
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wide">Business Profile</h3>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Business Description</label>
                  <textarea value={businessDescription} onChange={(e) => setBusinessDescription(e.target.value)} placeholder="What does this business do?" rows={3} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Ideal Customer</label>
                  <textarea value={idealCustomer} onChange={(e) => setIdealCustomer(e.target.value)} placeholder="Who is the ideal customer?" rows={2} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Main Problem Solved</label>
                  <textarea value={mainProblemSolved} onChange={(e) => setMainProblemSolved(e.target.value)} placeholder="What problem does this business solve?" rows={2} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Tone Preference</label>
                  <select value={tonePreference} onChange={(e) => setTonePreference(e.target.value)} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400">
                    <option value="">Select tone...</option>
                    <option value="professional">Professional</option>
                    <option value="casual">Casual</option>
                    <option value="friendly">Friendly</option>
                    <option value="authoritative">Authoritative</option>
                    <option value="conversational">Conversational</option>
                  </select>
                </div>
              </div>
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wide">Marketing Details</h3>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Platforms (comma-separated)</label>
                  <input type="text" value={platforms.join(', ')} onChange={(e) => handleArrayInput(e.target.value, setPlatforms)} placeholder="linkedin, twitter, blog" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Keywords (comma-separated)</label>
                  <input type="text" value={keywords.join(', ')} onChange={(e) => handleArrayInput(e.target.value, setKeywords)} placeholder="saas, productivity, automation" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Competitors (comma-separated)</label>
                  <input type="text" value={competitors.join(', ')} onChange={(e) => handleArrayInput(e.target.value, setCompetitors)} placeholder="CompanyA, CompanyB, CompanyC" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Customer Pain Points (comma-separated)</label>
                  <input type="text" value={customerPainPoints.join(', ')} onChange={(e) => handleArrayInput(e.target.value, setCustomerPainPoints)} placeholder="high costs, slow process, poor support" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-2">Customer Questions (comma-separated)</label>
                  <input type="text" value={customerQuestions.join(', ')} onChange={(e) => handleArrayInput(e.target.value, setCustomerQuestions)} placeholder="How much does it cost?, Is it easy to use?" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400" />
                </div>
              </div>
            </div>
            <div className="border-t border-neutral-200 dark:border-neutral-700 px-6 py-4 bg-neutral-50 dark:bg-neutral-800">
              <div className="flex justify-end gap-3">
                <button onClick={handleCancel} disabled={isSubmitting} className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed">Cancel</button>
                <button onClick={handleSubmit} disabled={isSubmitting || !name.trim()} className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed">
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
