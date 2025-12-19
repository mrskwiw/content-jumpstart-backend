import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/api/projects';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Building2, User, Target } from 'lucide-react';
import type { Project } from '@/types/domain';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (project: Project) => void;
}

interface FormData {
  name: string;
  clientId: string;
  clientName: string;
  packageTier: string;
}

export function NewProjectDialog({ open, onOpenChange, onSuccess }: Props) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<FormData>({
    name: '',
    clientId: '',
    clientName: '',
    packageTier: 'professional',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const createMutation = useMutation({
    mutationFn: (data: FormData) =>
      projectsApi.create({
        name: data.name,
        clientId: data.clientId,
        templates: [],
        platforms: [],
        tone: 'professional',
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      onSuccess?.(project);
      handleClose();
    },
  });

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.name.trim()) newErrors.name = 'Project name is required';
    if (!formData.clientId.trim()) newErrors.clientId = 'Client ID is required';
    if (!formData.clientName.trim()) newErrors.clientName = 'Client name is required';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      createMutation.mutate(formData);
    }
  };

  const handleClose = () => {
    setFormData({ name: '', clientId: '', clientName: '', packageTier: 'professional' });
    setErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
          <DialogDescription>
            Start a new content generation project for a client. You'll complete the full brief in the wizard.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Project Name */}
          <div>
            <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
              <Building2 className="h-4 w-4" />
              Project Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="March 2025 Campaign"
              className={`w-full rounded-md border px-3 py-2 text-sm ${
                errors.name ? 'border-rose-500' : 'border-slate-200'
              }`}
            />
            {errors.name && <p className="mt-1 text-xs text-rose-600">{errors.name}</p>}
          </div>

          {/* Client ID */}
          <div>
            <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
              <User className="h-4 w-4" />
              Client ID
            </label>
            <input
              type="text"
              value={formData.clientId}
              onChange={(e) => setFormData({ ...formData, clientId: e.target.value })}
              placeholder="acme-corp"
              className={`w-full rounded-md border px-3 py-2 text-sm ${
                errors.clientId ? 'border-rose-500' : 'border-slate-200'
              }`}
            />
            {errors.clientId && <p className="mt-1 text-xs text-rose-600">{errors.clientId}</p>}
            <p className="mt-1 text-xs text-slate-500">Lowercase, hyphenated identifier</p>
          </div>

          {/* Client Name */}
          <div>
            <label className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-800">
              <Target className="h-4 w-4" />
              Client Name
            </label>
            <input
              type="text"
              value={formData.clientName}
              onChange={(e) => setFormData({ ...formData, clientName: e.target.value })}
              placeholder="Acme Corp"
              className={`w-full rounded-md border px-3 py-2 text-sm ${
                errors.clientName ? 'border-rose-500' : 'border-slate-200'
              }`}
            />
            {errors.clientName && <p className="mt-1 text-xs text-rose-600">{errors.clientName}</p>}
          </div>

          {/* Package Tier */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-800">Package Tier</label>
            <select
              value={formData.packageTier}
              onChange={(e) => setFormData({ ...formData, packageTier: e.target.value })}
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="starter">Starter ($1,200)</option>
              <option value="professional">Professional ($1,800)</option>
              <option value="premium">Premium ($2,500)</option>
              <option value="enterprise">Enterprise ($3,500)</option>
            </select>
          </div>

          <DialogFooter>
            <button
              type="button"
              onClick={handleClose}
              className="rounded-md border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Project'}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
