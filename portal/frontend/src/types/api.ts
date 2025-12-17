// User types
export interface User {
  user_id: string
  email: string
  full_name: string
  company_name?: string
  role: string
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

// Project types
export interface Project {
  project_id: string
  user_id: string
  client_name: string
  status: string
  package_tier: string
  package_price: number
  posts_count: number
  revision_limit: number
  revisions_used: number
  submitted_at: string
  processing_started_at?: string
  completed_at?: string
  delivered_at?: string
  updated_at?: string
}

export interface ProjectListResponse {
  total: number
  projects: Project[]
}

export interface CreateProjectRequest {
  client_name: string
  package_tier: string
  package_price: number
  posts_count: number
  revision_limit: number
}

// Brief types
export interface Brief {
  brief_id: string
  project_id: string
  company_name: string
  business_description: string
  ideal_customer: string
  main_problem_solved: string
  tone_preference: string
  sample_posts?: string[]
  customer_pain_points?: string[]
  customer_questions?: string[]
  created_at: string
  updated_at: string
}

export interface BriefSubmitRequest {
  project_id: string
  company_name: string
  business_description: string
  ideal_customer: string
  main_problem_solved: string
  tone_preference: string
  sample_posts?: string[]
  customer_pain_points?: string[]
  customer_questions?: string[]
}

// Deliverable types
export interface Deliverable {
  deliverable_id: string
  project_id: string
  deliverable_type: string
  file_path: string
  file_format?: string
  download_count: number
  created_at: string
  last_downloaded_at?: string
}

export interface DeliverableListResponse {
  total: number
  deliverables: Deliverable[]
}

// Dashboard types
export interface DashboardStats {
  total_files: number
  total_deliverables: number
  brief_submitted: boolean
  days_since_created: number
}

export interface DashboardResponse {
  project_id: string
  client_name: string
  package_tier: string
  package_price: number
  status: string
  created_at: string
  updated_at: string
  stats: DashboardStats
  brief_id?: string
}

// File upload types
export interface FileUpload {
  file_id: string
  project_id: string
  original_filename: string
  stored_filename: string
  file_type: string
  file_size_bytes: number
  upload_date: string
}

export interface FileListResponse {
  total: number
  files: FileUpload[]
}

// Post types
export interface Post {
  post_id: string
  project_id: string
  content: string
  platform?: string
  status: string
  template_id?: number
  created_at: string
  updated_at: string
}

export interface PostListResponse {
  total: number
  posts: Post[]
}

export interface GeneratePostsRequest {
  num_posts?: number
  platform?: string
  regenerate?: boolean
}

export interface UpdatePostRequest {
  content: string
  status?: string
}

// Common response types
export interface ErrorResponse {
  detail: string | { loc: string[]; msg: string; type: string }[]
}
