// Mock API handlers using axios-mock-adapter alternative
// Simple mock implementation that can be toggled via environment variable

import type { AxiosInstance } from 'axios';
import { mockProjects, mockDeliverables, mockPosts, mockRuns, mockClients } from './data';
import type {
  Project,
  Deliverable,
  PostDraft,
  Run,
  MarkDeliveredInput,
  GenerateAllInput,
  RegenerateInput,
  ExportInput,
} from '@/types/domain';
import { getUseMocksEnabled } from '@/utils/env';

// Local request-shape types for the mock API (kept out of domain.ts).
interface ProjectListParams {
  search?: string;
  status?: string;
}
interface ProjectCreateInput {
  clientId: string;
  name: string;
  templates?: string[];
  platforms?: string[];
  tone?: string;
}
interface DeliverableListParams {
  status?: string;
  clientId?: string;
}
interface PostListParams {
  projectId?: string;
  runId?: string;
  status?: string;
}
interface RunListParams {
  projectId?: string;
}
interface LoginCredentials {
  email: string;
  password: string;
}
// Shape thrown by the mock handlers to short-circuit the axios request interceptor.
interface MockRejection {
  config: unknown;
  response: { data: unknown; status: number; config: unknown };
}

let mockEnabled = getUseMocksEnabled();

/**
 * Enable or disable mock handling explicitly.
 */
export function setMockEnabled(enabled: boolean) {
  mockEnabled = enabled;
}

/**
 * Check whether mocks are currently enabled.
 */
export function getMockEnabled() {
  return mockEnabled;
}

// Simple mock storage
const mockData = {
  projects: [...mockProjects],
  deliverables: [...mockDeliverables],
  posts: [...mockPosts],
  runs: [...mockRuns],
  clients: [...mockClients],
};

// Mock API functions (used as fallback when backend is unavailable)
export const mockApi = {
  projects: {
    list: async (params?: ProjectListParams) => {
      await delay(300);
      let filtered = [...mockData.projects];

      if (params?.search) {
        const search = params.search.toLowerCase();
        filtered = filtered.filter(
          (p) => p.name.toLowerCase().includes(search) || p.id.toLowerCase().includes(search)
        );
      }

      if (params?.status) {
        filtered = filtered.filter((p) => p.status === params.status);
      }

      return filtered;
    },

    get: async (id: string) => {
      await delay(200);
      const project = mockData.projects.find((p) => p.id === id);
      if (!project) throw new Error('Project not found');
      return project;
    },

    create: async (input: ProjectCreateInput) => {
      await delay(400);
      const newProject: Project = {
        id: `project-${Date.now()}`,
        clientId: input.clientId,
        name: input.name,
        status: 'draft',
        templates: input.templates || [],
        platforms: input.platforms || [],
        tone: input.tone,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      mockData.projects.push(newProject);
      return newProject;
    },

    update: async (id: string, input: Partial<Project>) => {
      await delay(300);
      const index = mockData.projects.findIndex((p) => p.id === id);
      if (index === -1) throw new Error('Project not found');
      mockData.projects[index] = {
        ...mockData.projects[index],
        ...input,
        updatedAt: new Date().toISOString(),
      };
      return mockData.projects[index];
    },
  },

  deliverables: {
    list: async (params?: DeliverableListParams) => {
      await delay(250);
      let filtered = [...mockData.deliverables];

      if (params?.status) {
        filtered = filtered.filter((d) => d.status === params.status);
      }

      if (params?.clientId) {
        filtered = filtered.filter((d) => d.clientId === params.clientId);
      }

      return filtered;
    },

    get: async (id: string) => {
      await delay(200);
      const deliverable = mockData.deliverables.find((d) => d.id === id);
      if (!deliverable) throw new Error('Deliverable not found');
      return deliverable;
    },

    markDelivered: async (id: string, input: MarkDeliveredInput) => {
      await delay(400);
      const index = mockData.deliverables.findIndex((d) => d.id === id);
      if (index === -1) throw new Error('Deliverable not found');
      mockData.deliverables[index] = {
        ...mockData.deliverables[index],
        status: 'delivered',
        deliveredAt: input.deliveredAt,
        proofUrl: input.proofUrl,
        proofNotes: input.proofNotes,
      };
      return mockData.deliverables[index];
    },
  },

  posts: {
    list: async (params?: PostListParams) => {
      await delay(300);
      let filtered = [...mockData.posts];

      if (params?.projectId) {
        filtered = filtered.filter((p) => p.projectId === params.projectId);
      }

      if (params?.runId) {
        filtered = filtered.filter((p) => p.runId === params.runId);
      }

      if (params?.status) {
        filtered = filtered.filter((p) => p.status === params.status);
      }

      return filtered;
    },

    get: async (id: string) => {
      await delay(200);
      const post = mockData.posts.find((p) => p.id === id);
      if (!post) throw new Error('Post not found');
      return post;
    },
  },

  runs: {
    list: async (params?: RunListParams) => {
      await delay(250);
      let filtered = [...mockData.runs];

      if (params?.projectId) {
        filtered = filtered.filter((r) => r.projectId === params.projectId);
      }

      return filtered;
    },

    get: async (id: string) => {
      await delay(200);
      const run = mockData.runs.find((r) => r.id === id);
      if (!run) throw new Error('Run not found');
      return run;
    },
  },

  generator: {
    generateAll: async (input: GenerateAllInput) => {
      const runId = `run-${Date.now()}`;
      const newRun: Run = {
        id: runId,
        projectId: input.projectId,
        isBatch: input.isBatch,
        startedAt: new Date().toISOString(),
        status: 'pending', // Start as pending, will transition to running then succeeded
        logs: [],
      };
      mockData.runs.push(newRun);

      // Simulate async generation in background
      setTimeout(() => {
        // Update to running
        const run = mockData.runs.find((r) => r.id === runId);
        if (run) {
          run.status = 'running';
          run.logs = ['Starting generation...', 'Analyzing client brief...'];
        }

        // After 2 more seconds, complete the generation
        setTimeout(() => {
          const run = mockData.runs.find((r) => r.id === runId);
          if (run) {
            run.status = 'succeeded';
            run.completedAt = new Date().toISOString();
            run.logs = ['Starting generation...', 'Analyzing client brief...', 'Generating posts...', 'Complete!'];

            // Create mock posts when generation completes
            const numPosts = input.templateQuantities
              ? Object.values(input.templateQuantities as Record<string, number>).reduce((sum: number, n: number) => sum + n, 0)
              : 30;

            for (let i = 1; i <= numPosts; i++) {
              const post: PostDraft = {
                id: `post-${Date.now()}-${i}`,
                projectId: input.projectId,
                runId: run.id,
                content: `Mock post content ${i} for project ${input.projectId}. This is a sample post generated by the mock API.`,
                createdAt: new Date().toISOString(),
                wordCount: 100 + Math.floor(Math.random() * 100),
                readabilityScore: 60 + Math.floor(Math.random() * 30),
                hasCta: Math.random() > 0.3,
                targetPlatform: 'linkedin',
                status: Math.random() > 0.7 ? 'flagged' : 'approved',
                flags: Math.random() > 0.7 ? ['too_short'] : [],
              };
              mockData.posts.push(post);
            }
          }
        }, 2000);
      }, 500);

      // Return immediately with pending run
      return newRun;
    },

    regenerate: async (input: RegenerateInput) => {
      await delay(1500);
      // Update flagged posts to approved
      input.postIds.forEach((postId: string) => {
        const index = mockData.posts.findIndex((p) => p.id === postId);
        if (index !== -1) {
          mockData.posts[index] = {
            ...mockData.posts[index],
            status: 'approved',
            flags: [],
            content: `Regenerated: ${mockData.posts[index].content}`,
          };
        }
      });
      return { success: true, regeneratedCount: input.postIds.length };
    },
  },

  export: {
    export: async (input: ExportInput) => {
      await delay(1000);
      // ExportInput.format is broader (txt|md|docx|html|json|wxr) than a stored
      // Deliverable.format (txt|md|docx); the real backend normalizes this. Narrow it
      // here so the fabricated mock Deliverable is well-typed, defaulting non-document
      // export formats to txt.
      const deliverableFormat: Deliverable['format'] =
        input.format === 'md' || input.format === 'docx' ? input.format : 'txt';
      const newDeliverable: Deliverable = {
        id: `deliv-${Date.now()}`,
        projectId: input.projectId,
        clientId: input.clientId,
        format: deliverableFormat,
        // Use the normalized format for the extension too, so format and path agree.
        path: `outputs/${input.clientId}/${input.projectId}-${new Date().toISOString().split('T')[0]}.${deliverableFormat}`,
        createdAt: new Date().toISOString(),
        status: 'ready',
        runId: mockData.runs.find((r) => r.projectId === input.projectId)?.id,
        checksum: `checksum-${Date.now()}`,
      };
      mockData.deliverables.push(newDeliverable);
      return newDeliverable;
    },
  },

  auth: {
    login: async (credentials: LoginCredentials) => {
      await delay(500);
      if (credentials.email === 'demo@example.com' && credentials.password === 'demo') {
        return {
          access_token: 'mock-access-token',
          refresh_token: 'mock-refresh-token',
          user: {
            id: 'user-1',
            email: 'demo@example.com',
            name: 'Demo Operator',
            role: 'operator',
          },
        };
      }
      throw new Error('Invalid credentials');
    },

    refresh: async (refreshToken: string) => {
      await delay(300);
      return {
        access_token: 'mock-access-token-refreshed',
        refresh_token: refreshToken,
      };
    },
  },
};

// Helper function to add realistic delay
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Export mock interceptor setup function
export function setupMockInterceptor(axiosInstance: AxiosInstance) {
  if (!mockEnabled) return;


  // Intercept requests and return mock data
  axiosInstance.interceptors.request.use(
    async (config) => {
      // Only mock if USE_MOCKS is enabled
      if (!mockEnabled) return config;

      const url = config.url || '';
      const method = config.method?.toUpperCase();

      try {
        // Auth endpoints
        if (url.includes('/api/auth/login') && method === 'POST') {
          const response = await mockApi.auth.login(config.data);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        if (url.includes('/api/auth/refresh') && method === 'POST') {
          const response = await mockApi.auth.refresh(config.data.refresh_token);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        // Projects endpoints
        if (url === '/api/projects' && method === 'GET') {
          const response = await mockApi.projects.list(config.params);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        if (url.match(/\/api\/projects\/[^/]+$/) && method === 'GET') {
          const id = url.split('/').pop()!;
          const response = await mockApi.projects.get(id);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        if (url === '/api/projects' && method === 'POST') {
          const response = await mockApi.projects.create(config.data);
          return Promise.reject({ config, response: { data: response, status: 201, config } });
        }

        // Deliverables endpoints
        if (url === '/api/deliverables' && method === 'GET') {
          const response = await mockApi.deliverables.list(config.params);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        if (url.match(/\/api\/deliverables\/[^/]+\/mark-delivered$/) && method === 'PATCH') {
          const id = url.split('/')[3];
          const response = await mockApi.deliverables.markDelivered(id, config.data);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        // Posts endpoints
        if (url === '/api/posts' && method === 'GET') {
          const response = await mockApi.posts.list(config.params);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        // Runs endpoints
        if (url === '/api/runs' && method === 'GET') {
          const response = await mockApi.runs.list(config.params);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        // Generator endpoints
        if (url === '/api/generator/generate-all' && method === 'POST') {
          const response = await mockApi.generator.generateAll(config.data);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        if (url === '/api/generator/regenerate' && method === 'POST') {
          const response = await mockApi.generator.regenerate(config.data);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        // Export endpoint
        if (url === '/api/export' && method === 'POST') {
          const response = await mockApi.export.export(config.data);
          return Promise.reject({ config, response: { data: response, status: 200, config } });
        }

        return config;
      } catch (mockError: unknown) {
        // Return mocked response
        if (
          mockError &&
          typeof mockError === 'object' &&
          'response' in mockError &&
          (mockError as MockRejection).response
        ) {
          return Promise.reject(mockError);
        }
        throw mockError;
      }
    },
    (error) => Promise.reject(error)
  );

  // Handle mock responses
  axiosInstance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response && mockEnabled) {
        // This is a mock response, return it as success
        return Promise.resolve(error.response);
      }
      return Promise.reject(error);
    }
  );
}
