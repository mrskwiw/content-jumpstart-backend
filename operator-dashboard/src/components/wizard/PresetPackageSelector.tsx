import { useState, useEffect, memo } from 'react';
import { Check, Zap, TrendingUp, Sparkles, ArrowRight, Loader2 } from 'lucide-react';

interface PresetPackage {
  tier: 'starter' | 'professional' | 'premium';
  name: string;
  description: string;
  templateQuantities: Record<number, number>;
  researchIncluded: boolean;
  price: number;
}

interface Props {
  initialSelection?: 'starter' | 'professional' | 'premium';
  onContinue?: (pkg: PresetPackage) => void;
}

export const PresetPackageSelector = memo(function PresetPackageSelector({
  initialSelection,
  onContinue,
}: Props) {
  const [packages, setPackages] = useState<PresetPackage[]>([]);
  const [selected, setSelected] = useState<'starter' | 'professional' | 'premium' | null>(
    initialSelection || null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch preset packages from API
  useEffect(() => {
    const fetchPackages = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/pricing/packages');

        if (!response.ok) {
          throw new Error('Failed to fetch preset packages');
        }

        const data = await response.json();
        setPackages(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load packages');
        console.error('Error fetching packages:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchPackages();
  }, []);

  const selectedPackage = packages.find((pkg) => pkg.tier === selected);

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case 'starter':
        return <Zap className="h-6 w-6" />;
      case 'professional':
        return <TrendingUp className="h-6 w-6" />;
      case 'premium':
        return <Sparkles className="h-6 w-6" />;
      default:
        return null;
    }
  };

  const getTierColor = (tier: string, selected: boolean) => {
    const colors = {
      starter: {
        border: selected ? 'border-emerald-600' : 'border-emerald-200',
        bg: selected ? 'bg-emerald-50' : 'bg-white',
        accent: 'bg-emerald-600',
        text: 'text-emerald-600',
        hoverBg: 'hover:bg-emerald-50',
      },
      professional: {
        border: selected ? 'border-blue-600' : 'border-blue-200',
        bg: selected ? 'bg-blue-50' : 'bg-white',
        accent: 'bg-blue-600',
        text: 'text-blue-600',
        hoverBg: 'hover:bg-blue-50',
      },
      premium: {
        border: selected ? 'border-purple-600' : 'border-purple-200',
        bg: selected ? 'bg-purple-50' : 'bg-white',
        accent: 'bg-purple-600',
        text: 'text-purple-600',
        hoverBg: 'hover:bg-purple-50',
      },
    };
    return colors[tier as keyof typeof colors] || colors.starter;
  };

  const getPackageFeatures = (pkg: PresetPackage) => {
    const totalPosts = Object.values(pkg.templateQuantities).reduce((sum, qty) => sum + qty, 0);
    const templateCount = Object.keys(pkg.templateQuantities).length;

    const features = [
      `${totalPosts} professional posts`,
      `${templateCount} template varieties`,
      'Unlimited revisions',
      'Brand voice guide',
      'Posting schedule',
    ];

    if (pkg.researchIncluded) {
      features.push('✨ Deep research included');
    }

    if (pkg.tier === 'premium') {
      features.push('Priority support');
    }

    return features;
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-slate-200 bg-white p-6">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-600" />
          <p className="mt-2 text-sm text-slate-600">Loading packages...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm font-medium text-red-800">Error loading packages</p>
        <p className="mt-1 text-xs text-red-600">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-900">Choose a Preset Package</h3>
        <p className="mt-1 text-sm text-slate-600">
          Professionally curated template mixes optimized for content variety and engagement.
        </p>
      </div>

      {/* Pricing info */}
      <div className="mb-6 rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-800">
        <strong>Flat $40/post pricing</strong> - No hidden fees, unlimited revisions included
      </div>

      {/* Package Cards */}
      <div className="grid gap-4 lg:grid-cols-3">
        {packages.map((pkg) => {
          const isSelected = selected === pkg.tier;
          const colors = getTierColor(pkg.tier, isSelected);
          const features = getPackageFeatures(pkg);
          const totalPosts = Object.values(pkg.templateQuantities).reduce((sum, qty) => sum + qty, 0);

          return (
            <button
              key={pkg.tier}
              onClick={() => setSelected(pkg.tier)}
              className={`group relative flex flex-col rounded-lg border-2 p-6 text-left transition-all ${colors.border} ${colors.bg} ${colors.hoverBg} ${
                isSelected ? 'shadow-lg' : 'shadow-sm hover:shadow-md'
              }`}
            >
              {/* Popular Badge */}
              {pkg.tier === 'professional' && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 transform">
                  <span className="rounded-full bg-blue-600 px-3 py-1 text-xs font-bold text-white shadow-md">
                    MOST POPULAR
                  </span>
                </div>
              )}

              {/* Selected Indicator */}
              {isSelected && (
                <div className="absolute right-4 top-4">
                  <div className={`rounded-full ${colors.accent} p-1`}>
                    <Check className="h-4 w-4 text-white" />
                  </div>
                </div>
              )}

              {/* Icon & Title */}
              <div className="mb-4 flex items-center gap-3">
                <div className={`rounded-lg ${colors.accent} p-2 text-white`}>
                  {getTierIcon(pkg.tier)}
                </div>
                <div>
                  <h4 className="text-sm font-medium uppercase tracking-wide text-slate-500">
                    {pkg.tier}
                  </h4>
                  <p className="text-lg font-bold text-slate-900">{pkg.name}</p>
                </div>
              </div>

              {/* Description */}
              <p className="mb-4 text-sm text-slate-600">{pkg.description}</p>

              {/* Price */}
              <div className="mb-6">
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold text-slate-900">${pkg.price.toLocaleString()}</span>
                  <span className="text-sm text-slate-500">one-time</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  ${(pkg.price / totalPosts).toFixed(2)}/post
                </div>
              </div>

              {/* Features */}
              <ul className="space-y-2">
                {features.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <Check className={`h-4 w-4 flex-shrink-0 ${colors.text}`} />
                    <span className="text-slate-700">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* Select Button */}
              <div className="mt-6 pt-4 border-t border-slate-200">
                <div className={`rounded-md px-4 py-2 text-center text-sm font-semibold ${
                  isSelected
                    ? `${colors.accent} text-white`
                    : `border border-slate-300 text-slate-700 group-hover:border-slate-400`
                }`}>
                  {isSelected ? '✓ Selected' : 'Select Package'}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Template Breakdown */}
      {selectedPackage && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h4 className="mb-3 text-sm font-semibold text-slate-900">
            Template Breakdown for {selectedPackage.name}
          </h4>
          <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(selectedPackage.templateQuantities)
              .sort(([, a], [, b]) => b - a)
              .map(([templateId, quantity]) => (
                <div key={templateId} className="flex items-center justify-between rounded bg-white px-3 py-2">
                  <span className="text-slate-700">Template #{templateId}</span>
                  <span className="font-semibold text-slate-900">{quantity} posts</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 flex items-center justify-between border-t border-slate-200 pt-4">
        <div className="text-sm text-slate-600">
          {!selected && 'Select a package to continue'}
          {selected && `${selectedPackage?.name} selected`}
        </div>
        <button
          onClick={() => selectedPackage && onContinue?.(selectedPackage)}
          disabled={!selected}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Continue to Generation
          {selectedPackage && (
            <span className="text-xs opacity-75">(${selectedPackage.price.toLocaleString()})</span>
          )}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
});
