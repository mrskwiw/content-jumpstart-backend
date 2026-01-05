import { useState } from 'react';
import { Card, CardContent, Button, Input, Textarea } from '@/components/ui';
import { AlertCircle, Plus, X, FileText } from 'lucide-react';
import { ContentAuditCollector } from './ContentAuditCollector';

interface ResearchDataCollectionPanelProps {
  selectedTools: string[];
  onContinue: (collectedData: Record<string, any>) => void;
  onBack: () => void;
}

// Tool data requirements mapping
const TOOL_DATA_REQUIREMENTS: Record<string, {
  fields: Array<{
    key: string;
    label: string;
    type: 'textarea' | 'text-list' | 'content-list' | 'text';
    required: boolean;
    min?: number;
    max?: number;
    placeholder?: string;
    helperText?: string;
  }>;
}> = {
  voice_analysis: {
    fields: [{
      key: 'content_samples',
      label: 'Content Samples',
      type: 'content-list',
      required: true,
      min: 5,
      max: 30,
      placeholder: 'Paste a sample of client\'s writing (blog post, LinkedIn post, email, etc.)',
      helperText: 'Provide 5-30 samples of the client\'s existing writing (minimum 50 characters each). More samples = better voice analysis.'
    }]
  },
  seo_keyword_research: {
    fields: [{
      key: 'main_topics',
      label: 'Main Topics',
      type: 'text-list',
      required: true,
      min: 1,
      placeholder: 'e.g., AI automation, content marketing, SEO strategy',
      helperText: 'List the main topics you want to research keywords for (minimum 1 topic).'
    }]
  },
  competitive_analysis: {
    fields: [{
      key: 'competitors',
      label: 'Competitors',
      type: 'text-list',
      required: true,
      min: 1,
      max: 5,
      placeholder: 'e.g., HubSpot, Mailchimp, ConvertKit',
      helperText: 'List 1-5 competitor names to analyze (only first 5 will be analyzed).'
    }]
  },
  content_gap_analysis: {
    fields: [{
      key: 'current_content_topics',
      label: 'Current Content Topics',
      type: 'textarea',
      required: true,
      min: 10,
      placeholder: 'Describe what content topics you currently cover or list specific topics...',
      helperText: 'Describe your current content topics or provide a comma-separated list (minimum 10 characters).'
    }]
  },
  content_audit: {
    fields: [{
      key: 'content_inventory',
      label: 'Content to Audit',
      type: 'content-list',
      required: true,
      min: 1,
      max: 100,
      placeholder: 'URLs will be auto-analyzed...',
      helperText: 'Paste URLs for quick import, or manually add content without URLs. Tool analyzes performance, identifies top/underperformers, and recommends updates, refreshes, or archives.'
    }]
  },
  market_trends_research: {
    fields: [{
      key: 'industry',
      label: 'Industry',
      type: 'text',
      required: false,
      placeholder: 'e.g., SaaS, Healthcare, E-commerce',
      helperText: 'Specify the industry for trend research (uses client profile if not provided).'
    }, {
      key: 'focus_areas',
      label: 'Focus Areas (Optional)',
      type: 'text-list',
      required: false,
      placeholder: 'e.g., AI tools, remote work, sustainability',
      helperText: 'Specific areas to emphasize in trend research.'
    }]
  },
  platform_strategy: {
    fields: [{
      key: 'current_platforms',
      label: 'Current Platforms (Optional)',
      type: 'text-list',
      required: false,
      placeholder: 'e.g., LinkedIn, Twitter, Blog',
      helperText: 'Platforms you currently use for content distribution.'
    }, {
      key: 'content_goals',
      label: 'Content Goals (Optional)',
      type: 'text',
      required: false,
      placeholder: 'e.g., awareness and leads, thought leadership, customer education',
      helperText: 'Specific business objectives for your content.'
    }]
  }
};

export function ResearchDataCollectionPanel({
  selectedTools,
  onContinue,
  onBack
}: ResearchDataCollectionPanelProps) {
  const [collectedData, setCollectedData] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Get all required fields for selected tools
  const requiredFields = selectedTools.flatMap(tool =>
    TOOL_DATA_REQUIREMENTS[tool]?.fields || []
  );

  const handleTextListChange = (key: string, value: string) => {
    // Store the raw string value directly without processing
    // Processing will happen during validation/submission
    setCollectedData(prev => ({ ...prev, [key]: value }));
    setErrors(prev => ({ ...prev, [key]: '' }));
  };

  const handleContentListChange = (key: string, index: number, value: string) => {
    const currentList = collectedData[key] || [];
    const newList = [...currentList];
    newList[index] = value;
    setCollectedData(prev => ({ ...prev, [key]: newList }));
    setErrors(prev => ({ ...prev, [key]: '' }));
  };

  const handleAddContentSample = (key: string) => {
    const currentList = collectedData[key] || [];
    setCollectedData(prev => ({ ...prev, [key]: [...currentList, ''] }));
  };

  const handleRemoveContentSample = (key: string, index: number) => {
    const currentList = collectedData[key] || [];
    const newList = currentList.filter((_: any, i: number) => i !== index);
    setCollectedData(prev => ({ ...prev, [key]: newList }));
  };

  const validateData = (): boolean => {
    const newErrors: Record<string, string> = {};
    let isValid = true;

    requiredFields.forEach(field => {
      const value = collectedData[field.key];

      if (field.required) {
        // For text-list fields, convert string to array for validation
        let processedValue = value;
        if (field.type === 'text-list' && typeof value === 'string') {
          processedValue = value.split(',').map(item => item.trim()).filter(item => item.length > 0);
        }

        if (!processedValue || (Array.isArray(processedValue) && processedValue.length === 0) || (typeof processedValue === 'string' && processedValue.trim().length === 0)) {
          newErrors[field.key] = `${field.label} is required`;
          isValid = false;
          return;
        }

        if (Array.isArray(processedValue)) {
          // Check minimum count
          if (field.min && processedValue.length < field.min) {
            newErrors[field.key] = `Minimum ${field.min} items required`;
            isValid = false;
            return;
          }

          // Check maximum count
          if (field.max && processedValue.length > field.max) {
            newErrors[field.key] = `Maximum ${field.max} items allowed`;
            isValid = false;
            return;
          }

          // For content samples, check each item length
          if (field.key === 'content_samples') {
            const validSamples = processedValue.filter((sample: string) => sample.length >= 50);
            if (validSamples.length < (field.min || 0)) {
              newErrors[field.key] = `At least ${field.min} samples must be 50+ characters`;
              isValid = false;
              return;
            }
          }
        } else if (typeof processedValue === 'string') {
          // Check minimum length
          if (field.min && value.length < field.min) {
            newErrors[field.key] = `Minimum ${field.min} characters required`;
            isValid = false;
            return;
          }
        }
      }
    });

    setErrors(newErrors);
    return isValid;
  };

  const handleContinue = () => {
    if (validateData()) {
      // Process text-list fields: convert strings to arrays
      const processedData = { ...collectedData };
      requiredFields.forEach(field => {
        if (field.type === 'text-list' && typeof processedData[field.key] === 'string') {
          processedData[field.key] = processedData[field.key]
            .split(',')
            .map((item: string) => item.trim())
            .filter((item: string) => item.length > 0);
        }
      });
      onContinue(processedData);
    }
  };

  // If no data is needed, skip this step
  if (requiredFields.length === 0) {
    onContinue({});
    return null;
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
            Additional Data Required
          </h3>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            The selected research tools need some additional information. Please provide the following data:
          </p>
        </div>

        <div className="space-y-6">
          {requiredFields.map(field => (
            <div key={field.key}>
              {field.type === 'text' && (
                <div>
                  <label className="mb-1 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {field.label}
                    {field.required && <span className="text-rose-500">*</span>}
                  </label>
                  <Input
                    value={collectedData[field.key] || ''}
                    onChange={(e) => {
                      setCollectedData(prev => ({ ...prev, [field.key]: e.target.value }));
                      setErrors(prev => ({ ...prev, [field.key]: '' }));
                    }}
                    placeholder={field.placeholder}
                    className={errors[field.key] ? 'border-rose-500' : ''}
                  />
                  {errors[field.key] && (
                    <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors[field.key]}</p>
                  )}
                  {field.helperText && (
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                  )}
                </div>
              )}

              {field.type === 'textarea' && (
                <div>
                  <label className="mb-1 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {field.label}
                    {field.required && <span className="text-rose-500">*</span>}
                  </label>
                  <Textarea
                    value={collectedData[field.key] || ''}
                    onChange={(e) => {
                      setCollectedData(prev => ({ ...prev, [field.key]: e.target.value }));
                      setErrors(prev => ({ ...prev, [field.key]: '' }));
                    }}
                    placeholder={field.placeholder}
                    rows={4}
                    className={errors[field.key] ? 'border-rose-500' : ''}
                  />
                  {errors[field.key] && (
                    <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors[field.key]}</p>
                  )}
                  {field.helperText && (
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                  )}
                </div>
              )}

              {field.type === 'text-list' && (
                <div>
                  <label className="mb-1 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {field.label}
                    {field.required && <span className="text-rose-500">*</span>}
                  </label>
                  <Textarea
                    value={collectedData[field.key] || ''}
                    onChange={(e) => handleTextListChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    rows={3}
                    className={errors[field.key] ? 'border-rose-500' : ''}
                  />
                  <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
                    Separate items with commas
                    {field.min && ` (minimum ${field.min})`}
                    {field.max && ` (maximum ${field.max})`}
                  </p>
                  {errors[field.key] && (
                    <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors[field.key]}</p>
                  )}
                  {field.helperText && (
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                  )}
                </div>
              )}

              {field.type === 'content-list' && (
                <div>
                  {/* Special handling for content_inventory (Content Audit) */}
                  {field.key === 'content_inventory' ? (
                    <ContentAuditCollector
                      value={collectedData[field.key] || []}
                      onChange={(pieces) => {
                        setCollectedData(prev => ({ ...prev, [field.key]: pieces }));
                        setErrors(prev => ({ ...prev, [field.key]: '' }));
                      }}
                      error={errors[field.key]}
                    />
                  ) : (
                    <>
                      <label className="mb-2 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                        <FileText className="h-4 w-4" />
                        {field.label}
                        {field.required && <span className="text-rose-500">*</span>}
                      </label>

                      <div className="space-y-3">
                        {(collectedData[field.key] || []).map((sample: string, index: number) => (
                          <div key={index} className="flex gap-2">
                            <Textarea
                              value={sample}
                              onChange={(e) => handleContentListChange(field.key, index, e.target.value)}
                              placeholder={`${field.placeholder} (${index + 1}/${field.max || '∞'})`}
                              rows={3}
                              className="flex-1"
                            />
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleRemoveContentSample(field.key, index)}
                              className="mt-1"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>

                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleAddContentSample(field.key)}
                        disabled={!!(field.max && (collectedData[field.key] || []).length >= field.max)}
                        className="mt-3"
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Add Sample ({(collectedData[field.key] || []).length}/{field.max || '∞'})
                      </Button>

                      {errors[field.key] && (
                        <p className="mt-2 text-xs text-rose-600 dark:text-rose-400 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors[field.key]}
                        </p>
                      )}
                      {field.helperText && (
                        <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 flex justify-between border-t border-neutral-200 dark:border-neutral-700 pt-4">
          <Button variant="secondary" onClick={onBack}>
            Back to Tool Selection
          </Button>
          <Button variant="primary" onClick={handleContinue}>
            Continue to Execute Tools
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
