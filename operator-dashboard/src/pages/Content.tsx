import { FileSearch, Filter, CheckCircle2, XCircle, Clock } from 'lucide-react';

export default function Content() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Content Review</h1>
        <p className="text-sm text-slate-600">
          Review and approve content across all projects
        </p>
      </header>

      {/* Status Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button className="border-b-2 border-blue-600 px-4 py-2 text-sm font-medium text-blue-600">
          All Posts
        </button>
        <button className="border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900">
          Pending Review
        </button>
        <button className="border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900">
          Approved
        </button>
        <button className="border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900">
          Archive
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
          <Filter className="h-4 w-4" />
          Filter by Project
        </button>
        <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
          <Filter className="h-4 w-4" />
          Filter by Template
        </button>
        <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
          <Filter className="h-4 w-4" />
          Filter by Platform
        </button>
      </div>

      {/* Coming Soon State */}
      <div className="rounded-lg border border-slate-200 bg-white p-12 shadow-sm">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="rounded-full bg-purple-100 p-4 mb-4">
            <FileSearch className="h-12 w-12 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 mb-2">
            Content Review Workflow Coming Soon
          </h3>
          <p className="text-sm text-slate-600 max-w-md mb-6">
            Cross-project content review system with bulk approval, filtering by template/platform, and quality flags.
          </p>
          <div className="rounded-lg bg-purple-50 border border-purple-200 px-4 py-3 text-sm text-purple-800">
            <strong>Priority 1 Feature</strong> - Implementation in progress
          </div>
        </div>
      </div>

      {/* Feature Preview */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <h4 className="font-semibold text-slate-900">Bulk Approval</h4>
          </div>
          <p className="text-sm text-slate-600">
            Select multiple posts and approve in one action
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-2 mb-2">
            <Filter className="h-5 w-5 text-blue-600" />
            <h4 className="font-semibold text-slate-900">Advanced Filtering</h4>
          </div>
          <p className="text-sm text-slate-600">
            Filter by project, template, platform, word count, and quality flags
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="h-5 w-5 text-amber-600" />
            <h4 className="font-semibold text-slate-900">Review Queue</h4>
          </div>
          <p className="text-sm text-slate-600">
            Prioritized queue showing oldest pending items first
          </p>
        </div>
      </div>
    </div>
  );
}
