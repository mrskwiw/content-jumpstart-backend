import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import Layout from '../components/Layout'
import { api } from '../lib/api'
import { ArrowLeft, AlertCircle } from 'lucide-react'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    clientName: '',
    clientCompany: '',
    clientEmail: '',
    packageTier: 'Professional',
    briefData: '',
    researchServices: {
      marketTrends: false,
      contentGap: false,
      contentAudit: false,
      platformStrategy: false,
      audienceResearch: false,
      contentCalendar: false,
    },
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const createProjectMutation = useMutation({
    mutationFn: (data: any) => api.createProject(data),
    onSuccess: (response) => {
      const projectId = response.data.project_id
      navigate(`/projects/${projectId}`)
    },
    onError: (error: any) => {
      setErrors({
        submit: error.response?.data?.detail || 'Failed to create project. Please try again.',
      })
    },
  })

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.clientName.trim()) {
      newErrors.clientName = 'Client name is required'
    }

    if (!formData.clientCompany.trim()) {
      newErrors.clientCompany = 'Company name is required'
    }

    if (!formData.clientEmail.trim()) {
      newErrors.clientEmail = 'Client email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.clientEmail)) {
      newErrors.clientEmail = 'Invalid email format'
    }

    if (!formData.briefData.trim()) {
      newErrors.briefData = 'Brief information is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    createProjectMutation.mutate({
      client_name: formData.clientName,
      client_company: formData.clientCompany,
      client_email: formData.clientEmail,
      package_tier: formData.packageTier,
      brief_data: formData.briefData,
    })
  }

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  const handleResearchToggle = (service: string) => {
    setFormData((prev) => ({
      ...prev,
      researchServices: {
        ...prev.researchServices,
        [service]: !prev.researchServices[service as keyof typeof prev.researchServices],
      },
    }))
  }

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

        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Create New Project</h1>
          <p className="mt-1 text-sm text-gray-600">
            Fill in the client information and project brief to get started.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Client Information Card */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Client Information</h2>

            <div className="space-y-4">
              {/* Client Name */}
              <div>
                <label htmlFor="clientName" className="block text-sm font-medium text-gray-700">
                  Client Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="clientName"
                  value={formData.clientName}
                  onChange={(e) => handleChange('clientName', e.target.value)}
                  className={`mt-1 block w-full rounded-md shadow-sm sm:text-sm ${
                    errors.clientName
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
                  }`}
                  placeholder="John Doe"
                />
                {errors.clientName && (
                  <p className="mt-1 text-sm text-red-600">{errors.clientName}</p>
                )}
              </div>

              {/* Client Company */}
              <div>
                <label htmlFor="clientCompany" className="block text-sm font-medium text-gray-700">
                  Company Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="clientCompany"
                  value={formData.clientCompany}
                  onChange={(e) => handleChange('clientCompany', e.target.value)}
                  className={`mt-1 block w-full rounded-md shadow-sm sm:text-sm ${
                    errors.clientCompany
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
                  }`}
                  placeholder="Acme Corporation"
                />
                {errors.clientCompany && (
                  <p className="mt-1 text-sm text-red-600">{errors.clientCompany}</p>
                )}
              </div>

              {/* Client Email */}
              <div>
                <label htmlFor="clientEmail" className="block text-sm font-medium text-gray-700">
                  Email Address <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  id="clientEmail"
                  value={formData.clientEmail}
                  onChange={(e) => handleChange('clientEmail', e.target.value)}
                  className={`mt-1 block w-full rounded-md shadow-sm sm:text-sm ${
                    errors.clientEmail
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
                  }`}
                  placeholder="john@example.com"
                />
                {errors.clientEmail && (
                  <p className="mt-1 text-sm text-red-600">{errors.clientEmail}</p>
                )}
              </div>

              {/* Package Tier */}
              <div>
                <label htmlFor="packageTier" className="block text-sm font-medium text-gray-700">
                  Package Tier
                </label>
                <select
                  id="packageTier"
                  value={formData.packageTier}
                  onChange={(e) => handleChange('packageTier', e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                >
                  <option value="Starter">Starter - $1,200</option>
                  <option value="Professional">Professional - $1,800 (Recommended)</option>
                </select>
                <p className="mt-1 text-sm text-gray-500">
                  Professional tier includes comprehensive brand voice guide and 2 revision rounds.
                </p>
              </div>
            </div>
          </div>

          {/* Research Services Card */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Research Services (Optional)</h2>
            <p className="text-sm text-gray-600 mb-4">
              Select additional research services to include with this project. These will be billed separately.
            </p>

            <div className="space-y-3">
              <div className="flex items-center">
                <input
                  id="marketTrends"
                  type="checkbox"
                  checked={formData.researchServices.marketTrends}
                  onChange={() => handleResearchToggle('marketTrends')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="marketTrends" className="ml-3 text-sm text-gray-700">
                  Market Trends Research
                </label>
              </div>

              <div className="flex items-center">
                <input
                  id="contentGap"
                  type="checkbox"
                  checked={formData.researchServices.contentGap}
                  onChange={() => handleResearchToggle('contentGap')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="contentGap" className="ml-3 text-sm text-gray-700">
                  Content Gap Analysis
                </label>
              </div>

              <div className="flex items-center">
                <input
                  id="contentAudit"
                  type="checkbox"
                  checked={formData.researchServices.contentAudit}
                  onChange={() => handleResearchToggle('contentAudit')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="contentAudit" className="ml-3 text-sm text-gray-700">
                  Content Audit
                </label>
              </div>

              <div className="flex items-center">
                <input
                  id="platformStrategy"
                  type="checkbox"
                  checked={formData.researchServices.platformStrategy}
                  onChange={() => handleResearchToggle('platformStrategy')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="platformStrategy" className="ml-3 text-sm text-gray-700">
                  Platform Strategy
                </label>
              </div>

              <div className="flex items-center">
                <input
                  id="audienceResearch"
                  type="checkbox"
                  checked={formData.researchServices.audienceResearch}
                  onChange={() => handleResearchToggle('audienceResearch')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="audienceResearch" className="ml-3 text-sm text-gray-700">
                  Audience Research
                </label>
              </div>

              <div className="flex items-center">
                <input
                  id="contentCalendar"
                  type="checkbox"
                  checked={formData.researchServices.contentCalendar}
                  onChange={() => handleResearchToggle('contentCalendar')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="contentCalendar" className="ml-3 text-sm text-gray-700">
                  Content Calendar Strategy
                </label>
              </div>
            </div>
          </div>

          {/* Project Brief Card */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Project Brief</h2>

            <div>
              <label htmlFor="briefData" className="block text-sm font-medium text-gray-700">
                Brief Details <span className="text-red-500">*</span>
              </label>
              <p className="mt-1 text-sm text-gray-500 mb-2">
                Include business description, target audience, pain points, brand voice, and any
                other relevant information.
              </p>
              <textarea
                id="briefData"
                value={formData.briefData}
                onChange={(e) => handleChange('briefData', e.target.value)}
                rows={12}
                className={`mt-1 block w-full rounded-md shadow-sm sm:text-sm ${
                  errors.briefData
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
                }`}
                placeholder="Example:

Company: Acme Analytics
Business: B2B SaaS platform for data visualization
Target Audience: Marketing directors at mid-size companies
Pain Points: Complex data, lack of insights, manual reporting
Brand Voice: Professional, data-driven, approachable
Tone: Educational but not condescending
..."
              />
              {errors.briefData && (
                <p className="mt-1 text-sm text-red-600">{errors.briefData}</p>
              )}
            </div>
          </div>

          {/* Error Message */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-800">{errors.submit}</p>
                </div>
              </div>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex justify-end space-x-3">
            <Link
              to="/projects"
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={createProjectMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createProjectMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Creating...
                </>
              ) : (
                'Create Project'
              )}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  )
}
