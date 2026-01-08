import { useState, useEffect, memo } from 'react';
import { ClientBriefSchema, type ClientBrief, type Platform } from '@/types/domain';
import { User, Building2, Target, Lightbulb, MessageSquare, Save } from 'lucide-react';
import { BriefImportSection, type ParsedBriefResponse } from './BriefImportSection';
import { ImportPreviewModal } from '../ui/ImportPreviewModal';

interface Props {
  projectId?: string;
  initialData?: Partial<ClientBrief>;
  onSave?: (brief: ClientBrief) => void | Promise<void>;
}

// Memoized to prevent re-renders when parent updates (Performance optimization - December 25, 2025)
export const ClientProfilePanel = memo(function ClientProfilePanel({ projectId: _projectId, initialData, onSave }: Props) {
  const [formData, setFormData] = useState<Partial<ClientBrief>>({
    companyName: initialData?.companyName || '',
    businessDescription: initialData?.businessDescription || '',
    idealCustomer: initialData?.idealCustomer || '',
    mainProblemSolved: initialData?.mainProblemSolved || '',
    tonePreference: initialData?.tonePreference || 'professional',
    platforms: initialData?.platforms || [],
    customerPainPoints: initialData?.customerPainPoints || [],
    customerQuestions: initialData?.customerQuestions || [],
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [painPoint, setPainPoint] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');

  // Brief import state
  const [showPreview, setShowPreview] = useState(false);
  const [importedData, setImportedData] = useState<ParsedBriefResponse | null>(null);

  // Update form when initialData changes (e.g., when selecting existing client)
  useEffect(() => {
    if (initialData) {
      setFormData({
        companyName: initialData.companyName || '',
        businessDescription: initialData.businessDescription || '',
        idealCustomer: initialData.idealCustomer || '',
        mainProblemSolved: initialData.mainProblemSolved || '',
        tonePreference: initialData.tonePreference || 'professional',
        platforms: initialData.platforms || [],
        customerPainPoints: initialData.customerPainPoints || [],
        customerQuestions: initialData.customerQuestions || [],
      });
    }
  }, [initialData]);

  const platformOptions: { value: Platform; label: string }[] = [
    { value: 'linkedin', label: 'LinkedIn' },
    { value: 'twitter', label: 'Twitter' },
    { value: 'blog', label: 'Blog' },
    { value: 'email', label: 'Email' },
    { value: 'generic', label: 'Generic' },
  ];

  const toneOptions = [
    'professional',
    'conversational',
    'authoritative',
    'friendly',
    'innovative',
    'educational',
  ];

  const togglePlatform = (platform: Platform) => {
    const current = formData.platforms || [];
    if (current.includes(platform)) {
      setFormData({ ...formData, platforms: current.filter((p) => p !== platform) });
    } else {
      setFormData({ ...formData, platforms: [...current, platform] });
    }
  };

  const addPainPoint = () => {
    if (painPoint.trim()) {
      setFormData({
        ...formData,
        customerPainPoints: [...(formData.customerPainPoints || []), painPoint.trim()],
      });
      setPainPoint('');
    }
  };

  const removePainPoint = (index: number) => {
    setFormData({
      ...formData,
      customerPainPoints: (formData.customerPainPoints || []).filter((_, i) => i !== index),
    });
  };

  const addQuestion = () => {
    if (question.trim()) {
      // Format as "Q: question | A: answer" or just question if no answer provided
      const formattedQA = answer.trim()
        ? `Q: ${question.trim()} | A: ${answer.trim()}`
        : question.trim();

      setFormData({
        ...formData,
        customerQuestions: [...(formData.customerQuestions || []), formattedQA],
      });
      setQuestion('');
      setAnswer('');
    }
  };

  const removeQuestion = (index: number) => {
    setFormData({
      ...formData,
      customerQuestions: (formData.customerQuestions || []).filter((_, i) => i !== index),
    });
  };

  // Brief import handlers
  const handleBriefImport = (parsed: ParsedBriefResponse) => {
    setImportedData(parsed);
    setShowPreview(true);
  };

  const handleConfirmImport = () => {
    if (!importedData) return;

    // Merge imported data with current form data
    const merged: Partial<ClientBrief> = { ...formData };

    // String fields: Use imported if current is empty
    const stringFields: (keyof ClientBrief)[] = [
      'companyName',
      'businessDescription',
      'idealCustomer',
      'mainProblemSolved',
      'tonePreference',
    ];

    stringFields.forEach((field) => {
      const importedValue = importedData.fields[field]?.value;
      if (importedValue && !merged[field]) {
        merged[field] = importedValue as any;
      }
    });

    // Array fields: Union without duplicates
    const arrayFields: (keyof ClientBrief)[] = [
      'platforms',
      'customerPainPoints',
      'customerQuestions',
    ];

    arrayFields.forEach((field) => {
      const currentArray = (merged[field] as any[]) || [];
      const importedArray = (importedData.fields[field]?.value as any[]) || [];
      merged[field] = [...new Set([...currentArray, ...importedArray])] as any;
    });

    setFormData(merged);
    setShowPreview(false);
    setImportedData(null);
  };

  const handleSubmit = async () => {
    try {
      const validated = ClientBriefSchema.parse(formData);
      setErrors({});
      setIsSubmitting(true);

      // onSave might be async, so await it
      await onSave?.(validated);

      setIsSubmitting(false);
    } catch (error: unknown) {
      setIsSubmitting(false);

      // Handle validation errors (Zod errors have .errors array)
      if (error && typeof error === 'object' && 'errors' in error && Array.isArray(error.errors)) {
        const fieldErrors: Record<string, string> = {};
        error.errors.forEach((err: unknown) => {
          if (err && typeof err === 'object' && 'path' in err && Array.isArray(err.path) && 'message' in err) {
            const field = String(err.path[0]);
            const message = typeof err.message === 'string' ? err.message : 'Invalid value';
            fieldErrors[field] = message;
          }
        });
        setErrors(fieldErrors);
      } else {
        // Handle other errors (e.g., API errors)
        console.error('Error saving profile:', error);
        alert('Failed to save profile. Please try again.');
      }
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-800 p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold text-slate-900 dark:text-neutral-100">Client Profile</h3>
      </div>
      <p className="mb-6 text-sm text-slate-600 dark:text-neutral-400">
        Gather essential information about the client, their business, and their target audience.
      </p>

      {/* Brief Import Section */}
      <BriefImportSection onImport={handleBriefImport} />

      <div className="space-y-6">
        {/* Company Name */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <User className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Company Name
          </label>
          <input
            type="text"
            value={formData.companyName}
            onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
            placeholder="Acme Corp"
            className={`w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 ${
              errors.companyName ? 'border-rose-500 dark:border-rose-400' : 'border-slate-200 dark:border-slate-700'
            }`}
          />
          {errors.companyName && <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors.companyName}</p>}
        </div>

        {/* Business Description */}
        <div>
          <label className="mb-1 flex items-center justify-between text-sm font-medium text-slate-800 dark:text-neutral-200">
            <span className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
              Business Description <span className="text-rose-500">*</span>
            </span>
            <span
              className={`text-xs ${
                (formData.businessDescription || '').length >= 70
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-slate-500 dark:text-neutral-400'
              }`}
            >
              {(formData.businessDescription || '').length}/70 characters
            </span>
          </label>
          <textarea
            value={formData.businessDescription}
            onChange={(e) => setFormData({ ...formData, businessDescription: e.target.value })}
            placeholder="We provide cloud-based project management software for small teams..."
            rows={4}
            className={`w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 ${
              errors.businessDescription ? 'border-rose-500 dark:border-rose-400' : 'border-slate-200 dark:border-slate-700'
            }`}
          />
          {errors.businessDescription && (
            <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors.businessDescription}</p>
          )}
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
            Required for research tools. Describe what your business does and what makes it unique.
          </p>
        </div>

        {/* Ideal Customer */}
        <div>
          <label className="mb-1 flex items-center justify-between text-sm font-medium text-slate-800 dark:text-neutral-200">
            <span className="flex items-center gap-2">
              <Target className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
              Target Audience <span className="text-rose-500">*</span>
            </span>
            <span
              className={`text-xs ${
                (formData.idealCustomer || '').length >= 20
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-slate-500 dark:text-neutral-400'
              }`}
            >
              {(formData.idealCustomer || '').length}/20 characters
            </span>
          </label>
          <textarea
            value={formData.idealCustomer}
            onChange={(e) => setFormData({ ...formData, idealCustomer: e.target.value })}
            placeholder="Small business owners with 5-20 employees who struggle with team coordination..."
            rows={3}
            className={`w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 ${
              errors.idealCustomer ? 'border-rose-500 dark:border-rose-400' : 'border-slate-200 dark:border-slate-700'
            }`}
          />
          {errors.idealCustomer && <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors.idealCustomer}</p>}
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
            Required for research tools. Who is your ideal customer or target audience?
          </p>
        </div>

        {/* Main Problem Solved */}
        <div>
          <label className="mb-1 flex items-center justify-between text-sm font-medium text-slate-800 dark:text-neutral-200">
            <span className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
              Main Problem Solved
            </span>
            <span
              className={`text-xs ${
                (formData.mainProblemSolved || '').length >= 30
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-slate-500 dark:text-neutral-400'
              }`}
            >
              {(formData.mainProblemSolved || '').length}/30 characters
            </span>
          </label>
          <textarea
            value={formData.mainProblemSolved}
            onChange={(e) => setFormData({ ...formData, mainProblemSolved: e.target.value })}
            placeholder="We eliminate the chaos of scattered communication and missed deadlines..."
            rows={3}
            className={`w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 ${
              errors.mainProblemSolved ? 'border-rose-500 dark:border-rose-400' : 'border-slate-200 dark:border-slate-700'
            }`}
          />
          {errors.mainProblemSolved && (
            <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors.mainProblemSolved}</p>
          )}
        </div>

        {/* Tone Preference */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <MessageSquare className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Tone Preference
          </label>
          <select
            value={formData.tonePreference}
            onChange={(e) => setFormData({ ...formData, tonePreference: e.target.value })}
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 px-3 py-2 text-sm"
          >
            {toneOptions.map((tone) => (
              <option key={tone} value={tone}>
                {tone.charAt(0).toUpperCase() + tone.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Platform Selection */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800 dark:text-neutral-200">Platforms</label>
          <div className="flex flex-wrap gap-2">
            {platformOptions.map((platform) => (
              <button
                key={platform.value}
                type="button"
                onClick={() => togglePlatform(platform.value)}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                  formData.platforms?.includes(platform.value)
                    ? 'border-blue-600 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-800'
                }`}
              >
                {platform.label}
              </button>
            ))}
          </div>
          {errors.platforms && <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors.platforms}</p>}
        </div>

        {/* Customer Pain Points */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800 dark:text-neutral-200">Customer Pain Points</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={painPoint}
              onChange={(e) => setPainPoint(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addPainPoint())}
              placeholder="Add a pain point..."
              className="flex-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={addPainPoint}
              className="rounded-md bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm font-medium text-slate-700 dark:text-neutral-200 hover:bg-slate-200 dark:hover:bg-slate-600"
            >
              Add
            </button>
          </div>
          {(formData.customerPainPoints || []).length > 0 && (
            <ul className="mt-2 space-y-1">
              {formData.customerPainPoints?.map((point, i) => (
                <li key={i} className="flex items-center justify-between rounded-md bg-slate-50 dark:bg-neutral-800 px-3 py-2 text-sm text-slate-900 dark:text-neutral-100">
                  <span>{point}</span>
                  <button onClick={() => removePainPoint(i)} className="text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-300">
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Customer Questions */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800 dark:text-neutral-200">Common Customer Questions & Answers</label>
          <div className="space-y-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Question: What do customers ask?"
              className="w-full rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
            />
            <div className="flex gap-2">
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Answer: Your response to this question..."
                rows={2}
                className="flex-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
              />
              <button
                type="button"
                onClick={addQuestion}
                disabled={!question.trim()}
                className="rounded-md bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm font-medium text-slate-700 dark:text-neutral-200 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed self-start"
              >
                Add
              </button>
            </div>
          </div>
          {(formData.customerQuestions || []).length > 0 && (
            <ul className="mt-2 space-y-2">
              {formData.customerQuestions?.map((q, i) => {
                // Parse Q&A format if present
                const hasFormat = q.includes('Q:') && q.includes('A:');
                const parts = hasFormat ? q.split('|').map(p => p.trim()) : [q];
                const questionPart = parts[0]?.replace('Q:', '').trim() || q;
                const answerPart = parts[1]?.replace('A:', '').trim();

                return (
                  <li key={i} className="rounded-md bg-slate-50 dark:bg-neutral-800 px-3 py-2 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 space-y-1">
                        <div className="font-medium text-slate-900 dark:text-neutral-100">
                          <span className="text-blue-600 dark:text-blue-400">Q:</span> {questionPart}
                        </div>
                        {answerPart && (
                          <div className="text-slate-700 dark:text-neutral-300 pl-4">
                            <span className="text-green-600 dark:text-green-400">A:</span> {answerPart}
                          </div>
                        )}
                      </div>
                      <button onClick={() => removeQuestion(i)} className="text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-300 flex-shrink-0">
                        ×
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Save Button */}
        <div className="flex justify-end border-t border-slate-200 dark:border-slate-700 pt-4">
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 dark:bg-blue-500 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="h-4 w-4" />
            {isSubmitting ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </div>

      {/* Import Preview Modal */}
      {importedData && (
        <ImportPreviewModal
          open={showPreview}
          onClose={() => setShowPreview(false)}
          onConfirm={handleConfirmImport}
          currentData={formData}
          importedData={importedData}
        />
      )}
    </div>
  );
});
