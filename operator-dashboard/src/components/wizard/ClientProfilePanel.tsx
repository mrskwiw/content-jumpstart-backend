import { useState, useEffect, memo } from 'react';
import { ClientBriefSchema, type ClientBrief } from '@/types/domain';
import { User, Building2, Target, Lightbulb, MessageSquare, Save, MapPin } from 'lucide-react';
import { BriefImportSection, type ParsedBriefResponse } from './BriefImportSection';
import { ImportPreviewModal } from '../ui/ImportPreviewModal';
import { ClientResearchSection } from './ClientResearchSection';
import { useQuery } from '@tanstack/react-query';
import { creditsApi } from '@/api/credits';

interface Props {
  projectId?: string;
  initialData?: Partial<ClientBrief>;
  onSave?: (brief: ClientBrief) => void | Promise<void>;
}

// Memoized to prevent re-renders when parent updates (Performance optimization - December 25, 2025)
export const ClientProfilePanel = memo(function ClientProfilePanel({ initialData, onSave }: Props) {
  const [formData, setFormData] = useState<Partial<ClientBrief>>({
    companyName: initialData?.companyName || '',
    founderName: initialData?.founderName || '',
    industry: initialData?.industry || '',
    location: initialData?.location || '',
    businessDescription: initialData?.businessDescription || '',
    idealCustomer: initialData?.idealCustomer || '',
    mainProblemSolved: initialData?.mainProblemSolved || '',
    tonePreference: initialData?.tonePreference || 'professional',
    toneToAvoid: initialData?.toneToAvoid || '',
    brandPersonality: initialData?.brandPersonality || [],
    dataUsage: initialData?.dataUsage || 'moderate',
    platforms: initialData?.platforms || [],
    customerPainPoints: initialData?.customerPainPoints || [],
    customerQuestions: initialData?.customerQuestions || [],
    keywords: initialData?.keywords || [],
    competitors: initialData?.competitors || [],
    stories: initialData?.stories || [],
    misconceptions: initialData?.misconceptions || [],
    measurableResults: initialData?.measurableResults || '',
    postingFrequency: initialData?.postingFrequency || '',
    mainCta: initialData?.mainCta || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: creditData } = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: () => creditsApi.getBalance(),
  });
  const [painPoint, setPainPoint] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [keyword, setKeyword] = useState('');
  const [competitor, setCompetitor] = useState('');
  const [personalityTrait, setPersonalityTrait] = useState('');
  const [story, setStory] = useState('');
  const [misconception, setMisconception] = useState('');

  // Brief import state
  const [showPreview, setShowPreview] = useState(false);
  const [importedData, setImportedData] = useState<ParsedBriefResponse | null>(null);

  // Update form when initialData changes (e.g., when selecting existing client).
  // This resyncs the editable form to a newly-loaded/selected client record (an
  // external data source that arrives asynchronously), so the setState is a
  // deliberate external->state sync rather than derived render state.
  useEffect(() => {
    if (initialData) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFormData({
        companyName: initialData.companyName || '',
        founderName: initialData.founderName || '',
        industry: initialData.industry || '',
        location: initialData.location || '',
        businessDescription: initialData.businessDescription || '',
        idealCustomer: initialData.idealCustomer || '',
        mainProblemSolved: initialData.mainProblemSolved || '',
        tonePreference: initialData.tonePreference || 'professional',
        toneToAvoid: initialData.toneToAvoid || '',
        brandPersonality: initialData.brandPersonality || [],
        dataUsage: initialData.dataUsage || 'moderate',
        platforms: initialData.platforms || [],
        customerPainPoints: initialData.customerPainPoints || [],
        customerQuestions: initialData.customerQuestions || [],
        keywords: initialData.keywords || [],
        competitors: initialData.competitors || [],
        stories: initialData.stories || [],
        misconceptions: initialData.misconceptions || [],
        measurableResults: initialData.measurableResults || '',
        postingFrequency: initialData.postingFrequency || '',
        mainCta: initialData.mainCta || '',
      });
    }
  }, [initialData]);

  const toneOptions = [
    'professional',
    'conversational',
    'authoritative',
    'friendly',
    'innovative',
    'educational',
  ];

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

  const addKeyword = () => {
    if (keyword.trim()) {
      setFormData({
        ...formData,
        keywords: [...(formData.keywords || []), keyword.trim()],
      });
      setKeyword('');
    }
  };

  const removeKeyword = (index: number) => {
    setFormData({
      ...formData,
      keywords: (formData.keywords || []).filter((_, i) => i !== index),
    });
  };

  const addCompetitor = () => {
    if (competitor.trim() && (formData.competitors || []).length < 5) {
      setFormData({
        ...formData,
        competitors: [...(formData.competitors || []), competitor.trim()],
      });
      setCompetitor('');
    }
  };

  const removeCompetitor = (index: number) => {
    setFormData({
      ...formData,
      competitors: (formData.competitors || []).filter((_, i) => i !== index),
    });
  };


  const addPersonalityTrait = () => {
    if (personalityTrait.trim()) {
      setFormData({ ...formData, brandPersonality: [...(formData.brandPersonality || []), personalityTrait.trim()] });
      setPersonalityTrait('');
    }
  };

  const removePersonalityTrait = (index: number) => {
    setFormData({ ...formData, brandPersonality: (formData.brandPersonality || []).filter((_, i) => i !== index) });
  };

  const addStory = () => {
    if (story.trim()) {
      setFormData({ ...formData, stories: [...(formData.stories || []), story.trim()] });
      setStory('');
    }
  };

  const removeStory = (index: number) => {
    setFormData({ ...formData, stories: (formData.stories || []).filter((_, i) => i !== index) });
  };

  const addMisconception = () => {
    if (misconception.trim()) {
      setFormData({ ...formData, misconceptions: [...(formData.misconceptions || []), misconception.trim()] });
      setMisconception('');
    }
  };

  const removeMisconception = (index: number) => {
    setFormData({ ...formData, misconceptions: (formData.misconceptions || []).filter((_, i) => i !== index) });
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
      'founderName',
      'industry',
      'location',
      'businessDescription',
      'idealCustomer',
      'mainProblemSolved',
      'tonePreference',
      'toneToAvoid',
      'dataUsage',
      'measurableResults',
      'postingFrequency',
      'mainCta',
    ];

    stringFields.forEach((field) => {
      let importedValue = importedData.fields[field]?.value;
      if (importedValue) {
        // Handle tonePreference being returned as array - take first element
        if (field === 'tonePreference' && Array.isArray(importedValue)) {
          importedValue = importedValue[0];
        }
        (merged as Record<string, unknown>)[field as string] = importedValue;
      }
    });

    // Array fields: Union without duplicates
    const arrayFields: (keyof ClientBrief)[] = [
      'platforms',
      'customerPainPoints',
      'customerQuestions',
      'keywords',
      'competitors',
      'brandPersonality',
      'stories',
      'misconceptions',
      'keyPhrases',
    ];

    arrayFields.forEach((field) => {
      const currentArray: string[] = Array.isArray(merged[field]) ? (merged[field] as string[]) : [];
      const importedArray: string[] = Array.isArray(importedData.fields[field]?.value)
        ? (importedData.fields[field]!.value as string[])
        : [];
      (merged as Record<string, unknown>)[field as string] = [...new Set([...currentArray, ...importedArray])];
    });

    setFormData(merged);
    setShowPreview(false);
    setImportedData(null);
  };

  const handleResearchApply = (researched: Partial<ClientBrief>) => {
    const next: Partial<ClientBrief> = { ...formData };
    // String fields: apply if current is empty
    const stringKeys = [
      'founderName', 'industry', 'businessDescription', 'idealCustomer',
      'mainProblemSolved', 'tonePreference', 'toneToAvoid', 'measurableResults',
      'postingFrequency', 'mainCta',
    ] as const;
    for (const k of stringKeys) {
      const v = researched[k] as string | undefined;
      if (v && !next[k]) {
        (next as Record<string, unknown>)[k] = v;
      }
    }
    // Array fields: union without duplicates
    const arrayKeys = [
      'customerPainPoints', 'customerQuestions', 'keywords', 'competitors',
      'brandPersonality', 'keyPhrases', 'platforms', 'stories', 'misconceptions',
    ] as const;
    for (const k of arrayKeys) {
      const existing = (next[k] as string[] | undefined) ?? [];
      const incoming = (researched[k] as string[] | undefined) ?? [];
      (next as Record<string, unknown>)[k] = [...new Set([...existing, ...incoming])];
    }
    setFormData(next);
  };

  const handleSubmit = async () => {
    try {
      // Use lenient schema for profile saves - strict minimums are for research tools (backend enforces)
      const ProfileSaveSchema = ClientBriefSchema.extend({
        businessDescription: ClientBriefSchema.shape.businessDescription.min(1, 'Business description is required'),
        idealCustomer: ClientBriefSchema.shape.idealCustomer.min(1, 'Target audience is required'),
      });
      const validated = ProfileSaveSchema.parse(formData);
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

      {/* Client Research Section */}
      <ClientResearchSection
        businessName={(formData.companyName as string) ?? ''}
        location={(formData.location as string) ?? ''}
        creditBalance={creditData?.balance}
        onApply={handleResearchApply}
      />

      <div className="space-y-6">
        {/* Company Name */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <User className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Company / Business Name
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

        {/* Founder Name */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <User className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Founder / Primary Voice Name
          </label>
          <input
            type="text"
            value={formData.founderName ?? ''}
            onChange={(e) => setFormData({ ...formData, founderName: e.target.value })}
            placeholder="e.g., Dr. Sarah Kim, John Smith"
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
          />
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
            Used in personal brand content templates.
          </p>
        </div>

        {/* Industry */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <Building2 className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Industry
          </label>
          <input
            type="text"
            value={formData.industry}
            onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
            placeholder="e.g., dental practice, medical equipment manufacturer, project management software"
            className={`w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 ${
              errors.industry ? 'border-rose-500 dark:border-rose-400' : 'border-slate-200 dark:border-slate-700'
            }`}
          />
          {errors.industry && <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors.industry}</p>}
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
            Be specific (defines direct competitors). Use "dental practice" not "healthcare", "accounting firm" not "finance". Auto-inferred if not provided.
          </p>
        </div>

        {/* Location */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <MapPin className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Location
          </label>
          <input
            type="text"
            value={formData.location}
            onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            placeholder="e.g., San Francisco, California, USA, Remote, Global"
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
          />
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
            Geographic area or regions served. Helps with location-aware content and market context.
          </p>
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

        {/* Tone to Avoid */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <MessageSquare className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Tone to Avoid
          </label>
          <input
            type="text"
            value={formData.toneToAvoid ?? ''}
            onChange={(e) => setFormData({ ...formData, toneToAvoid: e.target.value })}
            placeholder="e.g., salesy, corporate jargon, overly casual"
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
          />
        </div>

        {/* Brand Personality */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800 dark:text-neutral-200">Brand Personality Traits</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={personalityTrait}
              onChange={(e) => setPersonalityTrait(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addPersonalityTrait())}
              placeholder="e.g., Direct, Witty, Warm, Data-driven"
              className="flex-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
            />
            <button type="button" onClick={addPersonalityTrait} className="rounded-md bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm font-medium text-slate-700 dark:text-neutral-200 hover:bg-slate-200 dark:hover:bg-slate-600">Add</button>
          </div>
          {(formData.brandPersonality || []).length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1">
              {formData.brandPersonality?.map((trait, i) => (
                <li key={i} className="inline-flex items-center gap-1 rounded-full bg-orange-50 dark:bg-orange-900/20 px-3 py-1 text-sm text-orange-800 dark:text-orange-300">
                  <span>{trait}</span>
                  <button onClick={() => removePersonalityTrait(i)} className="text-orange-600 dark:text-orange-400 hover:text-orange-800 font-bold">×</button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">Choose 2–4 traits. Controls content voice and style.</p>
        </div>

        {/* Data Usage */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <Lightbulb className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Data & Statistics Usage
          </label>
          <select
            value={formData.dataUsage ?? 'moderate'}
            onChange={(e) => setFormData({ ...formData, dataUsage: e.target.value })}
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 px-3 py-2 text-sm"
          >
            <option value="heavy">Heavy — loves numbers and stats</option>
            <option value="moderate">Moderate — mix of story and data</option>
            <option value="minimal">Minimal — personal/anecdotal preferred</option>
          </select>
        </div>

        {/* Posting Frequency */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <MessageSquare className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Desired Posting Frequency
          </label>
          <input
            type="text"
            value={formData.postingFrequency ?? ''}
            onChange={(e) => setFormData({ ...formData, postingFrequency: e.target.value })}
            placeholder="e.g., 3-4x weekly, daily, 2x per week"
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
          />
        </div>

        {/* Main CTA */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <Target className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Primary Call to Action
          </label>
          <input
            type="text"
            value={formData.mainCta ?? ''}
            onChange={(e) => setFormData({ ...formData, mainCta: e.target.value })}
            placeholder="e.g., Book a free consultation, Download the guide"
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
          />
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
            Appended to every post. Use a statement, not a question.
          </p>
        </div>

        {/* Measurable Results */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-neutral-200">
            <Lightbulb className="h-4 w-4 text-slate-600 dark:text-neutral-400" />
            Measurable Results / Proof Points
          </label>
          <textarea
            value={formData.measurableResults ?? ''}
            onChange={(e) => setFormData({ ...formData, measurableResults: e.target.value })}
            placeholder="e.g., 90% of clients report lower anxiety, 47% of new clients are referrals, reduced sales cycle from 90 to 45 days"
            rows={3}
            className="w-full rounded-md border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
          />
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
            Stats, percentages, and outcomes used in content to build credibility.
          </p>
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

        {/* SEO Keywords */}
        <div>
          <label className="mb-2 flex items-center justify-between text-sm font-medium text-slate-800 dark:text-neutral-200">
            <span>SEO Keywords</span>
            <span className={`text-xs ${(formData.keywords || []).length >= 5 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-neutral-400'}`}>
              {(formData.keywords || []).length}/5 keywords {(formData.keywords || []).length >= 5 && '✓'}
            </span>
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addKeyword())}
              placeholder="Add a keyword (e.g., project management)"
              className="flex-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={addKeyword}
              className="rounded-md bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm font-medium text-slate-700 dark:text-neutral-200 hover:bg-slate-200 dark:hover:bg-slate-600"
            >
              Add
            </button>
          </div>
          {(formData.keywords || []).length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1">
              {formData.keywords?.map((kw, i) => (
                <li key={i} className="inline-flex items-center gap-1 rounded-full bg-blue-50 dark:bg-blue-900/20 px-3 py-1 text-sm text-blue-800 dark:text-blue-300">
                  <span>{kw}</span>
                  <button onClick={() => removeKeyword(i)} className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-bold">
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-slate-500 dark:text-neutral-400">
            {(formData.keywords || []).length >= 5
              ? '✓ You have 5+ keywords. SEO research tool is optional for this client.'
              : 'Add 5+ keywords to skip the SEO research tool, or use the SEO research tool to generate keywords automatically.'}
          </p>
        </div>

        {/* Competitors */}
        <div>
          <label className="mb-2 flex items-center justify-between text-sm font-medium text-slate-800 dark:text-neutral-200">
            <span>Competitors</span>
            <span className={`text-xs ${(formData.competitors || []).length >= 1 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-neutral-400'}`}>
              {(formData.competitors || []).length}/5 competitors {(formData.competitors || []).length >= 1 && '✓'}
            </span>
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={competitor}
              onChange={(e) => setCompetitor(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCompetitor())}
              placeholder="Add a competitor (e.g., HubSpot)"
              className="flex-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
              disabled={(formData.competitors || []).length >= 5}
            />
            <button
              type="button"
              onClick={addCompetitor}
              disabled={(formData.competitors || []).length >= 5}
              className="rounded-md bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm font-medium text-slate-700 dark:text-neutral-200 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add
            </button>
          </div>
          {(formData.competitors || []).length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1">
              {formData.competitors?.map((comp, i) => (
                <li key={i} className="inline-flex items-center gap-1 rounded-full bg-purple-50 dark:bg-purple-900/20 px-3 py-1 text-sm text-purple-800 dark:text-purple-300">
                  <span>{comp}</span>
                  <button onClick={() => removeCompetitor(i)} className="text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 font-bold">
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-slate-500 dark:text-neutral-400">
            {(formData.competitors || []).length >= 1
              ? '✓ Competitive Analysis tool will auto-populate with these competitors.'
              : 'Add 1-5 competitors to auto-populate the Competitive Analysis research tool.'}
          </p>
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

        {/* Stories */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800 dark:text-neutral-200">Stories / Founder Journey / Customer Wins</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={story}
              onChange={(e) => setStory(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addStory())}
              placeholder="e.g., Helped a client cut their sales cycle in half"
              className="flex-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
            />
            <button type="button" onClick={addStory} className="rounded-md bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm font-medium text-slate-700 dark:text-neutral-200 hover:bg-slate-200 dark:hover:bg-slate-600">Add</button>
          </div>
          {(formData.stories || []).length > 0 && (
            <ul className="mt-2 space-y-1">
              {formData.stories?.map((s, i) => (
                <li key={i} className="flex items-center justify-between rounded-md bg-slate-50 dark:bg-neutral-800 px-3 py-2 text-sm text-slate-900 dark:text-neutral-100">
                  <span>{s}</span>
                  <button onClick={() => removeStory(i)} className="text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-300">×</button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">Used in personal story and case study templates.</p>
        </div>

        {/* Misconceptions / Topics to Avoid */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800 dark:text-neutral-200">Industry Misconceptions / Topics to Avoid</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={misconception}
              onChange={(e) => setMisconception(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addMisconception())}
              placeholder="e.g., 'You need 10k followers to get clients'"
              className="flex-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 px-3 py-2 text-sm"
            />
            <button type="button" onClick={addMisconception} className="rounded-md bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm font-medium text-slate-700 dark:text-neutral-200 hover:bg-slate-200 dark:hover:bg-slate-600">Add</button>
          </div>
          {(formData.misconceptions || []).length > 0 && (
            <ul className="mt-2 space-y-1">
              {formData.misconceptions?.map((m, i) => (
                <li key={i} className="flex items-center justify-between rounded-md bg-slate-50 dark:bg-neutral-800 px-3 py-2 text-sm text-slate-900 dark:text-neutral-100">
                  <span>{m}</span>
                  <button onClick={() => removeMisconception(i)} className="text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-300">×</button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400">Myths or claims to debunk in content. Also used to avoid sensitive topics.</p>
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
