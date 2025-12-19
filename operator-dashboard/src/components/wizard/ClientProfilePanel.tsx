import { useState } from 'react';
import { ClientBriefSchema, type ClientBrief, type Platform } from '@/types/domain';
import { User, Building2, Target, Lightbulb, MessageSquare, Save } from 'lucide-react';

interface Props {
  projectId?: string;
  initialData?: Partial<ClientBrief>;
  onSave?: (brief: ClientBrief) => void;
}

export function ClientProfilePanel({ projectId: _projectId, initialData, onSave }: Props) {
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
  const [painPoint, setPainPoint] = useState('');
  const [question, setQuestion] = useState('');

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
      setFormData({
        ...formData,
        customerQuestions: [...(formData.customerQuestions || []), question.trim()],
      });
      setQuestion('');
    }
  };

  const removeQuestion = (index: number) => {
    setFormData({
      ...formData,
      customerQuestions: (formData.customerQuestions || []).filter((_, i) => i !== index),
    });
  };

  const handleSubmit = () => {
    try {
      const validated = ClientBriefSchema.parse(formData);
      setErrors({});
      onSave?.(validated);
    } catch (error: any) {
      const fieldErrors: Record<string, string> = {};
      error.errors?.forEach((err: any) => {
        const field = err.path[0];
        fieldErrors[field] = err.message;
      });
      setErrors(fieldErrors);
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Building2 className="h-5 w-5 text-blue-600" />
        <h3 className="text-lg font-semibold text-slate-900">Client Profile</h3>
      </div>
      <p className="mb-6 text-sm text-slate-600">
        Gather essential information about the client, their business, and their target audience.
      </p>

      <div className="space-y-6">
        {/* Company Name */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
            <User className="h-4 w-4" />
            Company Name
          </label>
          <input
            type="text"
            value={formData.companyName}
            onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
            placeholder="Acme Corp"
            className={`w-full rounded-md border px-3 py-2 text-sm ${
              errors.companyName ? 'border-rose-500' : 'border-slate-200'
            }`}
          />
          {errors.companyName && <p className="mt-1 text-xs text-rose-600">{errors.companyName}</p>}
        </div>

        {/* Business Description */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
            <Building2 className="h-4 w-4" />
            Business Description
          </label>
          <textarea
            value={formData.businessDescription}
            onChange={(e) => setFormData({ ...formData, businessDescription: e.target.value })}
            placeholder="We provide cloud-based project management software for small teams..."
            rows={3}
            className={`w-full rounded-md border px-3 py-2 text-sm ${
              errors.businessDescription ? 'border-rose-500' : 'border-slate-200'
            }`}
          />
          {errors.businessDescription && (
            <p className="mt-1 text-xs text-rose-600">{errors.businessDescription}</p>
          )}
        </div>

        {/* Ideal Customer */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
            <Target className="h-4 w-4" />
            Ideal Customer
          </label>
          <textarea
            value={formData.idealCustomer}
            onChange={(e) => setFormData({ ...formData, idealCustomer: e.target.value })}
            placeholder="Small business owners with 5-20 employees who struggle with team coordination..."
            rows={3}
            className={`w-full rounded-md border px-3 py-2 text-sm ${
              errors.idealCustomer ? 'border-rose-500' : 'border-slate-200'
            }`}
          />
          {errors.idealCustomer && <p className="mt-1 text-xs text-rose-600">{errors.idealCustomer}</p>}
        </div>

        {/* Main Problem Solved */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
            <Lightbulb className="h-4 w-4" />
            Main Problem Solved
          </label>
          <textarea
            value={formData.mainProblemSolved}
            onChange={(e) => setFormData({ ...formData, mainProblemSolved: e.target.value })}
            placeholder="We eliminate the chaos of scattered communication and missed deadlines..."
            rows={3}
            className={`w-full rounded-md border px-3 py-2 text-sm ${
              errors.mainProblemSolved ? 'border-rose-500' : 'border-slate-200'
            }`}
          />
          {errors.mainProblemSolved && (
            <p className="mt-1 text-xs text-rose-600">{errors.mainProblemSolved}</p>
          )}
        </div>

        {/* Tone Preference */}
        <div>
          <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
            <MessageSquare className="h-4 w-4" />
            Tone Preference
          </label>
          <select
            value={formData.tonePreference}
            onChange={(e) => setFormData({ ...formData, tonePreference: e.target.value })}
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
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
          <label className="mb-2 block text-sm font-medium text-slate-800">Platforms</label>
          <div className="flex flex-wrap gap-2">
            {platformOptions.map((platform) => (
              <button
                key={platform.value}
                type="button"
                onClick={() => togglePlatform(platform.value)}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                  formData.platforms?.includes(platform.value)
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                {platform.label}
              </button>
            ))}
          </div>
          {errors.platforms && <p className="mt-1 text-xs text-rose-600">{errors.platforms}</p>}
        </div>

        {/* Customer Pain Points */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800">Customer Pain Points</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={painPoint}
              onChange={(e) => setPainPoint(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addPainPoint())}
              placeholder="Add a pain point..."
              className="flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={addPainPoint}
              className="rounded-md bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            >
              Add
            </button>
          </div>
          {(formData.customerPainPoints || []).length > 0 && (
            <ul className="mt-2 space-y-1">
              {formData.customerPainPoints?.map((point, i) => (
                <li key={i} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                  <span>{point}</span>
                  <button onClick={() => removePainPoint(i)} className="text-rose-600 hover:text-rose-800">
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Customer Questions */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-800">Common Customer Questions</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addQuestion())}
              placeholder="What question do customers ask?"
              className="flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={addQuestion}
              className="rounded-md bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            >
              Add
            </button>
          </div>
          {(formData.customerQuestions || []).length > 0 && (
            <ul className="mt-2 space-y-1">
              {formData.customerQuestions?.map((q, i) => (
                <li key={i} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                  <span>{q}</span>
                  <button onClick={() => removeQuestion(i)} className="text-rose-600 hover:text-rose-800">
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Save Button */}
        <div className="flex justify-end border-t border-slate-200 pt-4">
          <button
            onClick={handleSubmit}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            <Save className="h-4 w-4" />
            Save Profile
          </button>
        </div>
      </div>
    </div>
  );
}
