import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import Layout from '../components/Layout'
import PostEditor from '../components/PostEditor'
import { api } from '../lib/api'
import {
  ArrowLeft,
  Calendar,
  Package,
  FileText,
  Upload,
  Download,
  CheckCircle,
  Clock,
  AlertCircle,
  Sparkles,
} from 'lucide-react'

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const [numPosts, setNumPosts] = useState(30)
  const [platform, setPlatform] = useState('LinkedIn')

  const { data: projectData, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  })

  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['project-dashboard', projectId],
    queryFn: () => api.getProjectDashboard(projectId!),
    enabled: !!projectId,
  })

  const { data: filesData } = useQuery({
    queryKey: ['project-files', projectId],
    queryFn: () => api.getProjectFiles(projectId!),
    enabled: !!projectId,
  })

  const { data: deliverablesData } = useQuery({
    queryKey: ['project-deliverables', projectId],
    queryFn: () => api.getProjectDeliverables(projectId!),
    enabled: !!projectId,
  })

  const { data: postsData, isLoading: postsLoading } = useQuery({
    queryKey: ['project-posts', projectId],
    queryFn: () => api.listPosts(projectId!),
    enabled: !!projectId,
  })

  const generateMutation = useMutation({
    mutationFn: ({ num_posts, platform }: { num_posts: number; platform: string }) =>
      api.generatePosts(projectId!, { num_posts, platform }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-posts', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  const updatePostMutation = useMutation({
    mutationFn: ({ postId, content, status }: { postId: string; content: string; status?: string }) =>
      api.updatePost(projectId!, postId, { content, status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-posts', projectId] })
    },
  })

  const project = projectData?.data
  const dashboard = dashboardData?.data
  const files = filesData?.data.files || []
  const deliverables = deliverablesData?.data.deliverables || []
  const posts = postsData?.data.posts || []

  const isLoading = projectLoading || dashboardLoading

  const handleGeneratePosts = async () => {
    await generateMutation.mutateAsync({ num_posts: numPosts, platform })
  }

  const handleSavePost = async (postId: string, content: string, status?: string) => {
    await updatePostMutation.mutateAsync({ postId, content, status })
  }

  const statusColors: Record<string, string> = {
    onboarding: 'bg-blue-100 text-blue-800',
    processing: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    delivered: 'bg-purple-100 text-purple-800',
  }

  const statusIcons: Record<string, any> = {
    onboarding: Clock,
    processing: AlertCircle,
    completed: CheckCircle,
    delivered: CheckCircle,
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading project details...</p>
        </div>
      </Layout>
    )
  }

  if (!project) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-red-600">Project not found</p>
          <Link to="/projects" className="text-primary-600 hover:text-primary-900 mt-4 inline-block">
            Back to Projects
          </Link>
        </div>
      </Layout>
    )
  }

  const StatusIcon = statusIcons[project.status] || Clock

  return (
    <Layout>
      <div>
        {/* Back Button */}
        <Link
          to="/projects"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Projects
        </Link>

        {/* Project Header */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{project.client_name}</h1>
              {project.client_company && (
                <p className="text-lg text-gray-600 mt-1">{project.client_company}</p>
              )}
              {project.client_email && (
                <p className="text-sm text-gray-500 mt-1">{project.client_email}</p>
              )}
            </div>
            <div className="flex flex-col items-end space-y-2">
              <span
                className={`px-3 py-1 inline-flex items-center text-sm font-semibold rounded-full ${
                  statusColors[project.status] || 'bg-gray-100 text-gray-800'
                }`}
              >
                <StatusIcon className="w-4 h-4 mr-1" />
                {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
              </span>
              {project.package_tier && (
                <span className="text-sm text-gray-600">
                  <Package className="w-4 h-4 inline mr-1" />
                  {project.package_tier}
                </span>
              )}
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-200 flex space-x-6 text-sm text-gray-600">
            <div className="flex items-center">
              <Calendar className="w-4 h-4 mr-1" />
              Created {new Date(project.created_at).toLocaleDateString()}
            </div>
            {project.delivery_date && (
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 mr-1" />
                Delivered {new Date(project.delivery_date).toLocaleDateString()}
              </div>
            )}
          </div>
        </div>

        {/* Dashboard Stats */}
        {dashboard && (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <FileText className="h-6 w-6 text-gray-400" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Posts</dt>
                      <dd className="text-2xl font-semibold text-gray-900">
                        {dashboard.posts_count || 0}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Upload className="h-6 w-6 text-blue-400" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Files</dt>
                      <dd className="text-2xl font-semibold text-gray-900">{files.length}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Download className="h-6 w-6 text-green-400" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Deliverables</dt>
                      <dd className="text-2xl font-semibold text-gray-900">
                        {deliverables.length}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <CheckCircle className="h-6 w-6 text-purple-400" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Progress</dt>
                      <dd className="text-2xl font-semibold text-gray-900">
                        {dashboard.completion_percentage || 0}%
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Brief Information */}
        {project.brief_data && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Brief Information</h2>
            <div className="prose max-w-none">
              <p className="text-gray-700 whitespace-pre-wrap">{project.brief_data}</p>
            </div>
          </div>
        )}

        {/* Uploaded Files */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Uploaded Files</h2>
          {files.length === 0 ? (
            <p className="text-gray-600">No files uploaded yet.</p>
          ) : (
            <div className="space-y-2">
              {files.map((file: any) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-md hover:bg-gray-50"
                >
                  <div className="flex items-center">
                    <FileText className="w-5 h-5 text-gray-400 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.original_filename}</p>
                      <p className="text-xs text-gray-500">
                        {file.file_type} • Uploaded {new Date(file.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Posts Section */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-gray-900">Generated Posts</h2>
            <div className="flex items-center space-x-3">
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="text-sm border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                disabled={generateMutation.isPending || project?.status === 'processing'}
              >
                <option value="LinkedIn">LinkedIn</option>
                <option value="Twitter">Twitter</option>
                <option value="Facebook">Facebook</option>
              </select>
              <input
                type="number"
                value={numPosts}
                onChange={(e) => setNumPosts(Number(e.target.value))}
                min="1"
                max="50"
                className="w-20 text-sm border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                disabled={generateMutation.isPending || project?.status === 'processing'}
              />
              <button
                onClick={handleGeneratePosts}
                disabled={generateMutation.isPending || project?.status === 'processing'}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400"
              >
                <Sparkles className="w-4 h-4 mr-2" />
                {generateMutation.isPending ? 'Generating...' : 'Generate Posts'}
              </button>
            </div>
          </div>

          {project?.status === 'processing' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
              <div className="flex">
                <Clock className="w-5 h-5 text-yellow-600 mr-2" />
                <div>
                  <h3 className="text-sm font-medium text-yellow-800">Generation in progress...</h3>
                  <p className="text-sm text-yellow-700 mt-1">
                    Posts are being generated. This may take a few minutes.
                  </p>
                </div>
              </div>
            </div>
          )}

          {postsLoading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-600">Loading posts...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No posts yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                Generate posts to get started with content creation
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post: any) => (
                <PostEditor
                  key={post.post_id}
                  post={post}
                  onSave={handleSavePost}
                  isLoading={updatePostMutation.isPending}
                />
              ))}
            </div>
          )}
        </div>

        {/* Deliverables */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Deliverables</h2>
          {deliverables.length === 0 ? (
            <p className="text-gray-600">No deliverables available yet.</p>
          ) : (
            <div className="space-y-2">
              {deliverables.map((deliverable: any) => (
                <div
                  key={deliverable.id}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-md hover:bg-gray-50"
                >
                  <div className="flex items-center">
                    <Download className="w-5 h-5 text-green-500 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {deliverable.deliverable_type}
                      </p>
                      <p className="text-xs text-gray-500">
                        Generated {new Date(deliverable.generated_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => api.downloadDeliverable(deliverable.id)}
                    className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                  >
                    <Download className="w-4 h-4 mr-1" />
                    Download
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
