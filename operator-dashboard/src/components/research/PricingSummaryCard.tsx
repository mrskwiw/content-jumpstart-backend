import React, { memo } from 'react';
import { Coins } from 'lucide-react';
import { PricingPreview } from '../../api/research';

interface PricingSummaryCardProps {
  pricing: PricingPreview;
  selectedCount: number;
}

export const PricingSummaryCard = memo(function PricingSummaryCard({ pricing, selectedCount }: PricingSummaryCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <PriceMetric
          label="Selected Tools"
          value={`${selectedCount} tool${selectedCount !== 1 ? 's' : ''}`}
          icon={null}
        />
        <PriceMetric
          label="Total Cost"
          value={`${pricing?.finalCost ?? 0} credits`}
          emphasized
          icon={<Coins className="h-4 w-4" />}
        />
      </div>

      {/* Credit Cost Info */}
      {selectedCount > 0 && (
        <div className="flex items-center gap-2 text-sm p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <Coins className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <span className="text-blue-700 dark:text-blue-300">
            ≈ ${((pricing?.finalCost ?? 0) * 2).toFixed(2)} at $2/credit
          </span>
        </div>
      )}
    </div>
  );
});

interface PriceMetricProps {
  label: string;
  value: string;
  color?: 'emerald' | 'blue' | 'gray';
  emphasized?: boolean;
  icon?: React.ReactNode;
}

const PriceMetric = memo(function PriceMetric({ label, value, color = 'gray', emphasized = false, icon }: PriceMetricProps) {
  const colorClasses = {
    emerald: 'text-emerald-600 dark:text-emerald-400',
    blue: 'text-blue-600 dark:text-blue-400',
    gray: 'text-gray-900 dark:text-gray-100',
  };

  return (
    <div className={`${emphasized ? 'bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3' : ''}`}>
      <div className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
        {icon}
        {label}
      </div>
      <div className={`text-lg font-bold ${colorClasses[color]}`}>{value}</div>
    </div>
  );
});
