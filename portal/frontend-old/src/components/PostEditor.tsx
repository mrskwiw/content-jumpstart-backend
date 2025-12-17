import { useState } from 'react'
import { Edit2, Save, X, Check } from 'lucide-react'

interface Post {
  post_id: string
  project_id: string
  post_number: number
  content: string
  template_name: string | null
  platform: string
  word_count: number
  status: string
  generated_at: string
  last_edited_at: string | null
}

interface PostEditorProps {
  post: Post
  onSave: (postId: string, content: string, status?: string) => Promise<void>
  isLoading?: boolean
}

export default function PostEditor({ post, onSave, isLoading = false }: PostEditorProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editedContent, setEditedContent] = useState(post.content)
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onSave(post.post_id, editedContent)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to save post:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setEditedContent(post.content)
    setIsEditing(false)
  }

  const handleApprove = async () => {
    setIsSaving(true)
    try {
      await onSave(post.post_id, post.content, 'final')
    } catch (error) {
      console.error('Failed to approve post:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-800',
    final: 'bg-green-100 text-green-800',
    needs_revision: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      {/* Post Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-sm font-semibold text-gray-700">Post #{post.post_number}</span>
            {post.template_name && (
              <span className="text-xs text-gray-500">• {post.template_name}</span>
            )}
          </div>
          <div className="flex items-center space-x-2 mt-1">
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                statusColors[post.status] || 'bg-gray-100 text-gray-800'
              }`}
            >
              {post.status}
            </span>
            <span className="text-xs text-gray-500">{post.word_count} words</span>
            <span className="text-xs text-gray-500">• {post.platform}</span>
          </div>
        </div>
        <div className="flex space-x-2">
          {!isEditing && post.status === 'draft' && (
            <button
              onClick={handleApprove}
              disabled={isSaving || isLoading}
              className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400"
              title="Approve post"
            >
              <Check className="w-3 h-3 mr-1" />
              Approve
            </button>
          )}
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              disabled={isLoading}
              className="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <Edit2 className="w-3 h-3 mr-1" />
              Edit
            </button>
          ) : (
            <>
              <button
                onClick={handleSave}
                disabled={isSaving || isLoading}
                className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400"
              >
                <Save className="w-3 h-3 mr-1" />
                {isSaving ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={handleCancel}
                disabled={isSaving || isLoading}
                className="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <X className="w-3 h-3 mr-1" />
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Post Content */}
      {isEditing ? (
        <textarea
          value={editedContent}
          onChange={(e) => setEditedContent(e.target.value)}
          className="w-full min-h-[200px] p-3 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500 font-sans text-sm"
          disabled={isSaving || isLoading}
        />
      ) : (
        <div className="prose max-w-none">
          <p className="text-gray-700 whitespace-pre-wrap text-sm">{post.content}</p>
        </div>
      )}

      {/* Post Footer */}
      <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500">
        <div className="flex justify-between">
          <span>Generated {new Date(post.generated_at).toLocaleString()}</span>
          {post.last_edited_at && (
            <span>Last edited {new Date(post.last_edited_at).toLocaleString()}</span>
          )}
        </div>
      </div>
    </div>
  )
}
