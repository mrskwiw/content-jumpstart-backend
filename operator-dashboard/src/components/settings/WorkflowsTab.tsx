import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Plus, Zap } from 'lucide-react';

interface WorkflowRule {
  id: string;
  name: string;
  trigger: string;
  action: string;
  enabled: boolean;
  config?: { qualityThreshold?: number; daysDelay?: number; minScore?: number };
}

const mockWorkflowRules: WorkflowRule[] = [
  { id: '2', name: 'Send client satisfaction survey', trigger: 'Days after delivery', action: 'Email satisfaction survey', enabled: true, config: { daysDelay: 14 } },
];

export function WorkflowsTab() {
  const queryClient = useQueryClient();
  const [workflowConfigs, setWorkflowConfigs] = useState<Record<string, WorkflowRule['config']>>({});

  const { data: workflowRules = mockWorkflowRules } = useQuery({
    queryKey: ['workflow-rules'],
    queryFn: async () => { await new Promise(r => setTimeout(r, 300)); return mockWorkflowRules; },
  });

  const toggleWorkflowMutation = useMutation({
    mutationFn: async (data: { id: string; enabled: boolean }) => { await new Promise(r => setTimeout(r, 300)); return data; },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflow-rules'] }),
  });

  const updateWorkflowConfig = (ruleId: string, configKey: string, value: number) => {
    setWorkflowConfigs(prev => ({ ...prev, [ruleId]: { ...prev[ruleId], [configKey]: value } }));
  };

  const getConfigValue = (rule: WorkflowRule, key: string): number => {
    const localConfig = workflowConfigs[rule.id];
    if (localConfig && key in localConfig) return (localConfig as Record<string, number>)[key];
    return rule.config?.[key as keyof typeof rule.config] ?? 0;
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 p-4">
        <div className="flex gap-2">
          <AlertCircle className="h-4 w-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-primary-900 dark:text-primary-100">Workflow Automation</p>
            <p className="text-sm text-primary-700 dark:text-primary-300 mt-1">Automate repetitive tasks with custom workflow rules. Rules are evaluated in real-time.</p>
          </div>
        </div>
      </div>

      {workflowRules.map(rule => (
        <div key={rule.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{rule.name}</h3>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" checked={rule.enabled} onChange={e => toggleWorkflowMutation.mutate({ id: rule.id, enabled: e.target.checked })} className="peer sr-only" />
                <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
              </label>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium text-neutral-700 dark:text-neutral-300">Trigger:</span>
                <span className="text-neutral-600 dark:text-neutral-400">{rule.trigger}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-neutral-700 dark:text-neutral-300">Action:</span>
                <span className="text-neutral-600 dark:text-neutral-400">{rule.action}</span>
              </div>
            </div>

            {rule.config && (
              <div className="space-y-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Configuration</h4>
                {rule.config.qualityThreshold !== undefined && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-neutral-700 dark:text-neutral-300">Quality Threshold</label>
                      <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{getConfigValue(rule, 'qualityThreshold')}%</span>
                    </div>
                    <input type="range" min="0" max="100" step="5" value={getConfigValue(rule, 'qualityThreshold')} onChange={e => updateWorkflowConfig(rule.id, 'qualityThreshold', parseInt(e.target.value))} className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-primary-600 dark:accent-primary-500" />
                    <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400"><span>0%</span><span>50%</span><span>100%</span></div>
                  </div>
                )}
                {rule.config.daysDelay !== undefined && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-neutral-700 dark:text-neutral-300">Days Delay</label>
                      <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{getConfigValue(rule, 'daysDelay')} days</span>
                    </div>
                    <input type="range" min="1" max="30" step="1" value={getConfigValue(rule, 'daysDelay')} onChange={e => updateWorkflowConfig(rule.id, 'daysDelay', parseInt(e.target.value))} className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-primary-600 dark:accent-primary-500" />
                    <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400"><span>1 day</span><span>15 days</span><span>30 days</span></div>
                  </div>
                )}
                {rule.config.minScore !== undefined && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-neutral-700 dark:text-neutral-300">Minimum Score</label>
                      <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{getConfigValue(rule, 'minScore')}%</span>
                    </div>
                    <input type="range" min="0" max="100" step="5" value={getConfigValue(rule, 'minScore')} onChange={e => updateWorkflowConfig(rule.id, 'minScore', parseInt(e.target.value))} className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-primary-600 dark:accent-primary-500" />
                    <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400"><span>0%</span><span>50%</span><span>100%</span></div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ))}

      <button className="w-full rounded-lg border-2 border-dashed border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 text-neutral-600 dark:text-neutral-400 hover:border-primary-400 dark:hover:border-primary-600 hover:text-primary-600 dark:hover:text-primary-400 transition-colors">
        <Plus className="h-5 w-5 mx-auto mb-2" />
        <span className="text-sm font-medium">Create New Workflow Rule</span>
      </button>

      {/* suppress unused import warning */}
      <span className="hidden"><Zap /></span>
    </div>
  );
}
