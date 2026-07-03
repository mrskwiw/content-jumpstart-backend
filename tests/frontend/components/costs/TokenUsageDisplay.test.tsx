/**
 * TokenUsageDisplay Component Tests
 *
 * Tests for the token usage inline display component with compact and detailed variants.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TokenUsageDisplay } from '@/components/costs/TokenUsageDisplay';

describe('TokenUsageDisplay', () => {
  describe('Compact Variant', () => {
    it('renders compact variant with basic token counts', () => {
      render(
        <TokenUsageDisplay
          inputTokens={1000}
          outputTokens={500}
          variant="compact"
        />
      );

      expect(screen.getByText(/1,500 tokens/i)).toBeInTheDocument();
    });

    it('renders cost with correct formatting for amounts >= $1', () => {
      render(
        <TokenUsageDisplay
          inputTokens={100000}
          outputTokens={50000}
          costUsd={1.25}
          variant="compact"
        />
      );

      expect(screen.getByText('$1.25')).toBeInTheDocument();
    });

    it('renders cost with 4 decimals for amounts < $1', () => {
      render(
        <TokenUsageDisplay
          inputTokens={1000}
          outputTokens={500}
          costUsd={0.0123}
          variant="compact"
        />
      );

      expect(screen.getByText('$0.0123')).toBeInTheDocument();
    });

    it('renders cache savings when cache tokens are present', () => {
      render(
        <TokenUsageDisplay
          inputTokens={1000}
          outputTokens={500}
          cacheReadTokens={10000}
          costUsd={0.05}
          variant="compact"
          showCacheSavings={true}
        />
      );

      // Cache savings = (10000 / 1M) * 2.7 = $0.027
      expect(screen.getByText(/-\$0.0270 saved/i)).toBeInTheDocument();
    });

    it('does not render cache savings when showCacheSavings is false', () => {
      render(
        <TokenUsageDisplay
          inputTokens={1000}
          outputTokens={500}
          cacheReadTokens={10000}
          costUsd={0.05}
          variant="compact"
          showCacheSavings={false}
        />
      );

      expect(screen.queryByText(/saved/i)).not.toBeInTheDocument();
    });

    it('handles zero tokens gracefully', () => {
      render(
        <TokenUsageDisplay
          inputTokens={0}
          outputTokens={0}
          variant="compact"
        />
      );

      expect(screen.getByText('0 tokens')).toBeInTheDocument();
    });
  });

  describe('Detailed Variant', () => {
    it('renders detailed variant with all token types', () => {
      render(
        <TokenUsageDisplay
          inputTokens={5000}
          outputTokens={3000}
          cacheCreationTokens={2000}
          cacheReadTokens={1000}
          variant="detailed"
        />
      );

      expect(screen.getByText('Token Usage')).toBeInTheDocument();
      expect(screen.getByText('Input Tokens')).toBeInTheDocument();
      expect(screen.getByText('5,000')).toBeInTheDocument();
      expect(screen.getByText('Output Tokens')).toBeInTheDocument();
      expect(screen.getByText('3,000')).toBeInTheDocument();
    });

    it('renders cache sections only when cache tokens present', () => {
      const { rerender } = render(
        <TokenUsageDisplay
          inputTokens={5000}
          outputTokens={3000}
          variant="detailed"
        />
      );

      expect(screen.queryByText('Cache Creation')).not.toBeInTheDocument();
      expect(screen.queryByText('Cache Read')).not.toBeInTheDocument();

      rerender(
        <TokenUsageDisplay
          inputTokens={5000}
          outputTokens={3000}
          cacheCreationTokens={2000}
          cacheReadTokens={1000}
          variant="detailed"
        />
      );

      expect(screen.getByText('Cache Creation')).toBeInTheDocument();
      expect(screen.getByText('Cache Read')).toBeInTheDocument();
      expect(screen.getAllByText('2,000')[0]).toBeInTheDocument();
      expect(screen.getAllByText('1,000')[0]).toBeInTheDocument();
    });

    it('renders total cost section when cost provided', () => {
      render(
        <TokenUsageDisplay
          inputTokens={10000}
          outputTokens={5000}
          costUsd={0.45}
          variant="detailed"
        />
      );

      expect(screen.getByText('Total Cost')).toBeInTheDocument();
      expect(screen.getByText('$0.4500')).toBeInTheDocument();
    });

    it('renders estimated cost with tilde prefix', () => {
      render(
        <TokenUsageDisplay
          inputTokens={10000}
          outputTokens={5000}
          estimatedCostUsd={0.50}
          variant="detailed"
        />
      );

      expect(screen.getByText(/~\$0\.5000/)).toBeInTheDocument();
    });

    it('prefers actual cost over estimated cost', () => {
      render(
        <TokenUsageDisplay
          inputTokens={10000}
          outputTokens={5000}
          costUsd={0.45}
          estimatedCostUsd={0.50}
          variant="detailed"
        />
      );

      expect(screen.getByText('$0.4500')).toBeInTheDocument();
      expect(screen.queryByText(/~\$/)).not.toBeInTheDocument();
    });

    it('renders cache savings in detailed view', () => {
      render(
        <TokenUsageDisplay
          inputTokens={10000}
          outputTokens={5000}
          cacheReadTokens={20000}
          costUsd={0.50}
          variant="detailed"
          showCacheSavings={true}
        />
      );

      expect(screen.getByText('Cache Savings')).toBeInTheDocument();
      // Cache savings = (20000 / 1M) * 2.7 = $0.054
      expect(screen.getByText('$0.0540')).toBeInTheDocument();
    });
  });

  describe('Cost Color Coding', () => {
    it('applies emerald color for costs < $0.01', () => {
      const { container } = render(
        <TokenUsageDisplay
          inputTokens={100}
          outputTokens={50}
          costUsd={0.005}
          variant="compact"
        />
      );

      const costElement = container.querySelector('.text-emerald-600');
      expect(costElement).toBeInTheDocument();
    });

    it('applies blue color for costs $0.01-$0.10', () => {
      const { container } = render(
        <TokenUsageDisplay
          inputTokens={1000}
          outputTokens={500}
          costUsd={0.05}
          variant="compact"
        />
      );

      const costElement = container.querySelector('.text-blue-600');
      expect(costElement).toBeInTheDocument();
    });

    it('applies amber color for costs $0.10-$1.00', () => {
      const { container } = render(
        <TokenUsageDisplay
          inputTokens={10000}
          outputTokens={5000}
          costUsd={0.50}
          variant="compact"
        />
      );

      const costElement = container.querySelector('.text-amber-600');
      expect(costElement).toBeInTheDocument();
    });

    it('applies red color for costs >= $1.00', () => {
      const { container } = render(
        <TokenUsageDisplay
          inputTokens={100000}
          outputTokens={50000}
          costUsd={5.00}
          variant="compact"
        />
      );

      const costElement = container.querySelector('.text-red-600');
      expect(costElement).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles missing optional props gracefully', () => {
      render(
        <TokenUsageDisplay
          variant="compact"
        />
      );

      expect(screen.getByText('0 tokens')).toBeInTheDocument();
    });

    it('handles very large token counts', () => {
      render(
        <TokenUsageDisplay
          inputTokens={1_000_000}
          outputTokens={500_000}
          variant="compact"
        />
      );

      expect(screen.getByText('1,500,000 tokens')).toBeInTheDocument();
    });

    it('handles fractional cents correctly', () => {
      render(
        <TokenUsageDisplay
          inputTokens={10}
          outputTokens={5}
          costUsd={0.0001}
          variant="detailed"
        />
      );

      expect(screen.getByText('$0.0001')).toBeInTheDocument();
    });

    it('defaults to compact variant when variant not specified', () => {
      const { container } = render(
        <TokenUsageDisplay
          inputTokens={1000}
          outputTokens={500}
        />
      );

      // Compact variant has specific inline-flex class
      const compactElement = container.querySelector('.inline-flex');
      expect(compactElement).toBeInTheDocument();
    });
  });
});
