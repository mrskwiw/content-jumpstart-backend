/**
 * Smoke tests for WizardStepper component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { WizardStepper } from '../WizardStepper';

describe('WizardStepper Component', () => {
  const mockSteps = [
    { id: 'step1', label: 'Step 1', description: 'First step' },
    { id: 'step2', label: 'Step 2', description: 'Second step' },
  ];

  const mockOnStepClick = jest.fn();

  it('should render without crashing', () => {
    const { container } = render(
      <WizardStepper
        steps={mockSteps}
        currentStep={0}
        onStepClick={mockOnStepClick}
      />
    );
    expect(container).toBeInTheDocument();
  });

  it('should render all steps', () => {
    const { container } = render(
      <WizardStepper
        steps={mockSteps}
        currentStep={0}
        onStepClick={mockOnStepClick}
      />
    );
    expect(container).toHaveTextContent('Step 1');
    expect(container).toHaveTextContent('Step 2');
  });

  it('should render step buttons', () => {
    const { container } = render(
      <WizardStepper
        steps={mockSteps}
        currentStep={0}
        onStepClick={mockOnStepClick}
      />
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBe(mockSteps.length);
  });
});
