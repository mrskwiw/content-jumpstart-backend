# Enhanced Deliverable Drawer - Implementation Plan

## Date: December 19, 2025

## Feature #3: Enhanced Deliverable Drawer (Priority 0-3)

---

## Current State Analysis

### Existing Implementation
**Frontend** (`operator-dashboard/src/components/deliverables/DeliverableDrawer.tsx`):
- Simple side panel (46 lines)
- Displays: ID, format, path, run ID, checksum, status
- No tabs, no preview, no related data
- Uses basic div-based drawer (not a Radix component)

**Backend** (`backend/routers/deliverables.py`):
- `GET /api/deliverables/{id}` - Returns basic deliverable
- No extended details endpoint
- No file preview capability
- No related data aggregation

**Dependencies**:
- ✅ Has `@radix-ui/react-dialog`
- ❌ Missing `@radix-ui/react-tabs`
- ❌ Missing `react-syntax-highlighter`
- ✅ Has `date-fns` for date formatting
- ✅ Has `lucide-react` for icons

### Data Model Relationships
```
Deliverable
├── belongs_to: Project (via project_id)
├── belongs_to: Client (via client_id)
└── belongs_to: Run (via run_id, optional)

Run
└── has_many: Posts (via run.posts relationship)

Post
├── belongs_to: Project (via project_id)
└── belongs_to: Run (via run_id)
```

**Key Insight**: Can get posts related to a deliverable through `run_id`:
```python
deliverable.run.posts  # All posts from the same run
```

---

## Target State Design

### Tabbed Interface

```
┌─────────────────────────────────────────────────┐
│ Deliverable del-abc123          [X]            │
│ ┌──────────────────────────────────────────┐   │
│ │ Overview │ Preview │ Posts │ QA │ History│   │
│ └──────────────────────────────────────────┘   │
│                                                  │
│ [Tab Content Here]                              │
│                                                  │
│                                                  │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Tab Contents

#### 1. Overview Tab
Display metadata and status information:
- **Format**: DOCX, TXT, etc.
- **File Size**: Human-readable (from `file_size_bytes`)
- **Created**: Formatted date
- **Delivered**: Date if delivered, "Not delivered" otherwise
- **Status**: Badge with color coding
- **Project**: Name and ID
- **Client**: Name and ID
- **Run ID**: Link to run details (if available)
- **Checksum**: Full checksum value
- **Path**: Monospace font for file path
- **Proof URL**: Link if available
- **Proof Notes**: Text if available

#### 2. Preview Tab
Show file content preview:
- Read first 5000 characters from file
- Syntax highlighting for markdown files
- Plain text for .txt and .docx
- Error handling if file not found
- "Download full file" button
- Character count indicator

#### 3. Posts Tab
List all posts from the same run:
- Show if `run_id` is present
- Display post cards with:
  - Template name
  - Word count
  - Readability score
  - Status badge (approved/flagged)
  - First 150 characters of content
  - Flags if any
- Empty state if no run_id or no posts
- Total post count header

#### 4. QA Tab
Quality metrics summary:
- **From Post Data**:
  - Average readability score
  - Word count distribution
  - CTA presence percentage
  - Flagged posts count
  - Most common flags
- **From QA Report File** (if exists):
  - Parse `qa_report.md` from same directory
  - Show quality scores
  - Show validation results
- Empty state if no QA data available

#### 5. History Tab (Simplified for MVP)
Delivery and modification timeline:
- Created at
- Delivered at (if delivered)
- Last modified (file system)
- Status changes (future: audit log)
- Download count (future: tracking table)

**Note**: Full download tracking requires new database table. For MVP, show basic timeline only.

---

## Implementation Plan

### Phase 3A: Backend - Create Extended Details Endpoint

#### 3A.1: Create Extended Response Schema

**File**: `backend/schemas/deliverable.py`

Add new schema class:

```python
from typing import List, Dict, Optional

class PostSummary(BaseModel):
    """Summary of a post for deliverable details"""
    id: str
    template_name: Optional[str] = None
    word_count: Optional[int] = None
    readability_score: Optional[float] = None
    status: str
    flags: Optional[List[str]] = None
    content_preview: str  # First 150 chars

    model_config = ConfigDict(from_attributes=True)


class QASummary(BaseModel):
    """Quality assurance summary"""
    avg_readability: Optional[float] = None
    avg_word_count: Optional[float] = None
    total_posts: int = 0
    flagged_count: int = 0
    approved_count: int = 0
    cta_percentage: Optional[float] = None
    common_flags: List[str] = []


class DeliverableDetailResponse(DeliverableResponse):
    """Extended deliverable response with all details"""
    file_preview: Optional[str] = None  # First 5000 chars
    file_preview_truncated: bool = False
    posts: List[PostSummary] = []
    qa_summary: Optional[QASummary] = None

    # Timeline data
    file_modified_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
```

#### 3A.2: Create Service Function

**File**: `backend/services/deliverable_service.py` (NEW)

```python
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from models import Deliverable, Post
from schemas.deliverable import DeliverableDetailResponse, PostSummary, QASummary
from services import crud


def get_file_preview(file_path: Path, max_chars: int = 5000) -> tuple[Optional[str], bool]:
    """
    Read file preview.

    Returns:
        (content, was_truncated)
    """
    if not file_path.exists():
        return None, False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(max_chars + 1)
            truncated = len(content) > max_chars
            if truncated:
                content = content[:max_chars]
            return content, truncated
    except Exception as e:
        return f"Error reading file: {str(e)}", False


def calculate_qa_summary(posts: List[Post]) -> Optional[QASummary]:
    """Calculate QA summary from posts"""
    if not posts:
        return None

    total = len(posts)
    flagged = sum(1 for p in posts if p.status == 'flagged')
    approved = sum(1 for p in posts if p.status == 'approved')

    # Calculate averages
    readability_scores = [p.readability_score for p in posts if p.readability_score is not None]
    avg_readability = sum(readability_scores) / len(readability_scores) if readability_scores else None

    word_counts = [p.word_count for p in posts if p.word_count is not None]
    avg_word_count = sum(word_counts) / len(word_counts) if word_counts else None

    # CTA percentage
    posts_with_cta = sum(1 for p in posts if p.has_cta)
    cta_percentage = (posts_with_cta / total * 100) if total > 0 else None

    # Common flags
    all_flags = []
    for p in posts:
        if p.flags:
            all_flags.extend(p.flags)

    from collections import Counter
    flag_counts = Counter(all_flags)
    common_flags = [flag for flag, count in flag_counts.most_common(5)]

    return QASummary(
        avg_readability=avg_readability,
        avg_word_count=avg_word_count,
        total_posts=total,
        flagged_count=flagged,
        approved_count=approved,
        cta_percentage=cta_percentage,
        common_flags=common_flags,
    )


def get_deliverable_details(db: Session, deliverable_id: str) -> Optional[DeliverableDetailResponse]:
    """Get deliverable with extended details"""
    # Get base deliverable
    deliverable = crud.get_deliverable(db, deliverable_id)
    if not deliverable:
        return None

    # Get file preview
    file_path = Path("data/outputs") / deliverable.path
    file_preview, was_truncated = get_file_preview(file_path)

    # Get file modified time
    file_modified_at = None
    if file_path.exists():
        file_modified_at = datetime.fromtimestamp(file_path.stat().st_mtime)

    # Get posts if run_id exists
    posts = []
    qa_summary = None
    if deliverable.run_id:
        run_posts = db.query(Post).filter(Post.run_id == deliverable.run_id).all()

        # Create post summaries
        posts = [
            PostSummary(
                id=p.id,
                template_name=p.template_name,
                word_count=p.word_count,
                readability_score=p.readability_score,
                status=p.status,
                flags=p.flags,
                content_preview=p.content[:150] + "..." if len(p.content) > 150 else p.content
            )
            for p in run_posts
        ]

        # Calculate QA summary
        qa_summary = calculate_qa_summary(run_posts)

    # Build response
    return DeliverableDetailResponse(
        **deliverable.__dict__,
        file_preview=file_preview,
        file_preview_truncated=was_truncated,
        posts=posts,
        qa_summary=qa_summary,
        file_modified_at=file_modified_at,
    )
```

#### 3A.3: Create API Endpoint

**File**: `backend/routers/deliverables.py`

Add new endpoint:

```python
from services.deliverable_service import get_deliverable_details
from schemas.deliverable import DeliverableDetailResponse

@router.get("/{deliverable_id}/details", response_model=DeliverableDetailResponse)
async def get_deliverable_details_endpoint(
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get deliverable with extended details including:
    - File preview
    - Related posts
    - QA summary
    - Timeline data
    """
    details = get_deliverable_details(db, deliverable_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deliverable not found"
        )
    return details
```

---

### Phase 3B: Frontend - Install Dependencies

```bash
cd operator-dashboard
npm install @radix-ui/react-tabs
npm install react-syntax-highlighter
npm install @types/react-syntax-highlighter --save-dev
```

---

### Phase 4: Frontend - Implement Tabbed Drawer

#### 4.1: Update TypeScript Types

**File**: `operator-dashboard/src/types/domain.ts`

Add new types:

```typescript
export const PostSummarySchema = z.object({
  id: z.string(),
  templateName: z.string().optional(),
  wordCount: z.number().optional(),
  readabilityScore: z.number().optional(),
  status: z.string(),
  flags: z.array(z.string()).optional(),
  contentPreview: z.string(),
});
export type PostSummary = z.infer<typeof PostSummarySchema>;

export const QASummarySchema = z.object({
  avgReadability: z.number().optional(),
  avgWordCount: z.number().optional(),
  totalPosts: z.number(),
  flaggedCount: z.number(),
  approvedCount: z.number(),
  ctaPercentage: z.number().optional(),
  commonFlags: z.array(z.string()),
});
export type QASummary = z.infer<typeof QASummarySchema>;

export const DeliverableDetailsSchema = DeliverableSchema.extend({
  filePreview: z.string().optional(),
  filePreviewTruncated: z.boolean(),
  posts: z.array(PostSummarySchema),
  qaSummary: QASummarySchema.optional(),
  fileModifiedAt: z.string().datetime().optional(),
});
export type DeliverableDetails = z.infer<typeof DeliverableDetailsSchema>;
```

#### 4.2: Create API Function

**File**: `operator-dashboard/src/api/deliverables.ts`

Add method to existing API client:

```typescript
async getDetails(deliverableId: string): Promise<DeliverableDetails> {
  const { data } = await apiClient.get(`/api/deliverables/${deliverableId}/details`);
  return DeliverableDetailsSchema.parse(data);
}
```

#### 4.3: Create Tab Components

**File**: `operator-dashboard/src/components/deliverables/tabs/OverviewTab.tsx` (NEW)

```typescript
import type { DeliverableDetails } from '@/types/domain';
import { formatFileSize } from '@/utils/formatters';
import { format } from 'date-fns';

interface Props {
  deliverable: DeliverableDetails;
}

export function OverviewTab({ deliverable }: Props) {
  return (
    <div className="space-y-4 p-4">
      {/* Format & Size */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Format</div>
          <div className="mt-1 text-sm font-medium">{deliverable.format.toUpperCase()}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">File Size</div>
          <div className="mt-1 text-sm">{formatFileSize(deliverable.fileSizeBytes)}</div>
        </div>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Created</div>
          <div className="mt-1 text-sm">{format(new Date(deliverable.createdAt), 'PPp')}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Delivered</div>
          <div className="mt-1 text-sm">
            {deliverable.deliveredAt
              ? format(new Date(deliverable.deliveredAt), 'PPp')
              : <span className="text-slate-400">Not delivered</span>
            }
          </div>
        </div>
      </div>

      {/* Status */}
      <div>
        <div className="text-xs font-medium text-slate-500 uppercase">Status</div>
        <div className="mt-1">
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
            deliverable.status === 'delivered' ? 'bg-green-100 text-green-800' :
            deliverable.status === 'ready' ? 'bg-blue-100 text-blue-800' :
            'bg-slate-100 text-slate-800'
          }`}>
            {deliverable.status}
          </span>
        </div>
      </div>

      {/* IDs */}
      <div>
        <div className="text-xs font-medium text-slate-500 uppercase">Deliverable ID</div>
        <div className="mt-1 font-mono text-xs text-slate-700">{deliverable.id}</div>
      </div>

      {deliverable.runId && (
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Run ID</div>
          <div className="mt-1 font-mono text-xs text-slate-700">{deliverable.runId}</div>
        </div>
      )}

      {/* Path */}
      <div>
        <div className="text-xs font-medium text-slate-500 uppercase">File Path</div>
        <div className="mt-1 font-mono text-xs text-slate-700 break-all">{deliverable.path}</div>
      </div>

      {/* Checksum */}
      {deliverable.checksum && (
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase">Checksum</div>
          <div className="mt-1 font-mono text-xs text-slate-700 break-all">{deliverable.checksum}</div>
        </div>
      )}

      {/* Proof */}
      {(deliverable.proofUrl || deliverable.proofNotes) && (
        <div className="pt-4 border-t border-slate-200">
          <div className="text-xs font-medium text-slate-500 uppercase mb-2">Delivery Proof</div>
          {deliverable.proofUrl && (
            <div className="mb-2">
              <a
                href={deliverable.proofUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                View Proof
              </a>
            </div>
          )}
          {deliverable.proofNotes && (
            <div className="text-sm text-slate-600">{deliverable.proofNotes}</div>
          )}
        </div>
      )}
    </div>
  );
}
```

**File**: `operator-dashboard/src/components/deliverables/tabs/PreviewTab.tsx` (NEW)

**File**: `operator-dashboard/src/components/deliverables/tabs/PostsTab.tsx` (NEW)

**File**: `operator-dashboard/src/components/deliverables/tabs/QATab.tsx` (NEW)

**File**: `operator-dashboard/src/components/deliverables/tabs/HistoryTab.tsx` (NEW)

(Content for these tabs to be implemented in Phase 4)

#### 4.4: Rewrite Main Drawer Component

**File**: `operator-dashboard/src/components/deliverables/DeliverableDrawer.tsx`

Complete rewrite with tabs:

```typescript
import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import { deliverablesApi } from '@/api/deliverables';
import type { Deliverable } from '@/types/domain';
import { OverviewTab } from './tabs/OverviewTab';
import { PreviewTab } from './tabs/PreviewTab';
import { PostsTab } from './tabs/PostsTab';
import { QATab } from './tabs/QATab';
import { HistoryTab } from './tabs/HistoryTab';

interface Props {
  deliverable: Deliverable | null;
  onClose: () => void;
}

export function DeliverableDrawer({ deliverable, onClose }: Props) {
  const { data: details, isLoading, error } = useQuery({
    queryKey: ['deliverable-details', deliverable?.id],
    queryFn: () => deliverable ? deliverablesApi.getDetails(deliverable.id) : null,
    enabled: !!deliverable,
  });

  if (!deliverable) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/30">
      <div className="h-full w-full max-w-2xl bg-white shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <p className="text-lg font-semibold text-slate-900">
              Deliverable Details
            </p>
            <p className="text-sm text-slate-500 font-mono">{deliverable.id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-slate-500">Loading...</div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800">
                  Error loading deliverable details
                </p>
              </div>
            </div>
          )}

          {details && (
            <Tabs.Root defaultValue="overview" className="flex flex-col h-full">
              <Tabs.List className="flex border-b border-slate-200 px-6 bg-slate-50">
                <Tabs.Trigger
                  value="overview"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Overview
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="preview"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Preview
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="posts"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Posts ({details.posts.length})
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="qa"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Quality
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="history"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  History
                </Tabs.Trigger>
              </Tabs.List>

              <Tabs.Content value="overview" className="flex-1">
                <OverviewTab deliverable={details} />
              </Tabs.Content>

              <Tabs.Content value="preview" className="flex-1">
                <PreviewTab deliverable={details} />
              </Tabs.Content>

              <Tabs.Content value="posts" className="flex-1">
                <PostsTab deliverable={details} />
              </Tabs.Content>

              <Tabs.Content value="qa" className="flex-1">
                <QATab deliverable={details} />
              </Tabs.Content>

              <Tabs.Content value="history" className="flex-1">
                <HistoryTab deliverable={details} />
              </Tabs.Content>
            </Tabs.Root>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## Testing Strategy

### Backend Tests

**File**: `backend/tests/test_deliverable_service.py` (NEW)

```python
def test_get_file_preview_success()
def test_get_file_preview_not_found()
def test_get_file_preview_truncation()
def test_calculate_qa_summary()
def test_get_deliverable_details_with_posts()
def test_get_deliverable_details_without_run()
```

### Frontend Tests

**File**: `operator-dashboard/src/components/deliverables/__tests__/DeliverableDrawer.test.tsx`

- Test tabs render correctly
- Test loading state
- Test error state
- Test empty states

### Manual Testing Checklist

- [ ] Drawer opens when clicking deliverable
- [ ] All 5 tabs are visible
- [ ] Overview tab shows all metadata
- [ ] Preview tab shows file content
- [ ] Posts tab shows posts when run_id exists
- [ ] Posts tab shows empty state when no run_id
- [ ] QA tab shows summary when posts exist
- [ ] QA tab shows empty state when no posts
- [ ] History tab shows timeline
- [ ] Close button works
- [ ] Loading state displays correctly
- [ ] Error state displays correctly

---

## Success Metrics

### Functional
- ✅ Users can view all deliverable details in one place
- ✅ File preview works for text/markdown files
- ✅ Posts display correctly when available
- ✅ QA summary calculates accurately
- ✅ All tabs load in <500ms

### Technical
- ✅ TypeScript compiles without errors
- ✅ No runtime errors
- ✅ Accessible (keyboard navigation works)
- ✅ Responsive design

### User Experience
- ✅ Reduced time to find deliverable info (from multiple pages to one drawer)
- ✅ Better understanding of deliverable quality
- ✅ Easier verification before delivery

---

## Implementation Order

1. ✅ **Exploration Complete** - Understand current state
2. **Planning** (Current) - Design solution
3. **Backend Implementation**:
   - Create schemas
   - Create service functions
   - Create API endpoint
   - Test backend
4. **Frontend Dependencies**:
   - Install npm packages
5. **Frontend Implementation**:
   - Update TypeScript types
   - Create API function
   - Create tab components
   - Rewrite main drawer
   - Test frontend
6. **Integration Testing**:
   - Manual testing
   - Fix bugs
7. **Documentation**:
   - Update completion summary
   - Commit and push

---

## Risks & Mitigation

### Risk 1: Large File Preview
**Issue**: Reading large files could be slow
**Mitigation**: Limit to 5000 characters, add loading indicator

### Risk 2: Missing Dependencies
**Issue**: Syntax highlighter adds bundle size
**Mitigation**: Use code splitting, lazy load preview tab

### Risk 3: Complex QA Calculation
**Issue**: Calculating stats from many posts could be slow
**Mitigation**: Compute in backend, cache if needed

### Risk 4: No Posts for Deliverable
**Issue**: Old deliverables may not have run_id
**Mitigation**: Show helpful empty state, explain why

---

## Future Enhancements (Not in MVP)

1. **Download Tracking**:
   - New table: `deliverable_downloads`
   - Track user, timestamp, IP
   - Show download count and history

2. **File Preview for Binary Files**:
   - DOCX preview using docx.js
   - PDF preview using pdf.js

3. **Editable Notes**:
   - Add notes field to deliverable
   - Allow operators to add context

4. **Related Files**:
   - Show all files from same run
   - Group by type (posts, QA, keywords)

---

**Status**: Planning Complete - Ready for Implementation
**Next Phase**: Phase 3 - Backend Implementation
