# Deliverables Interface Enhancement Plan

## Date: 2025-12-19

## Overview
This plan outlines the implementation strategy for enhancing the deliverables interface based on the gaps identified in the analysis phase. We'll prioritize features by impact and implementation complexity.

---

## Priority 0: Critical Features (Implement First)

### 1. File Download System

#### Backend Implementation
**File**: `backend/routers/deliverables.py`

```python
@router.get("/{deliverable_id}/download")
async def download_deliverable(
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download deliverable file"""
    # 1. Get deliverable from DB
    # 2. Validate file exists
    # 3. Return FileResponse with proper headers
```

**Technical Approach**:
- Use `FileResponse` from `fastapi.responses`
- Set `Content-Disposition: attachment` header
- Add filename from deliverable path
- Set appropriate `media_type` based on format
- Handle missing files gracefully (404)
- Add audit logging for downloads

**Security**:
- Validate path with `isSafeRelativePath()`
- Check user has access to client (authorization)
- Rate limit downloads (10 per minute per user)

**Error Handling**:
- 404 if deliverable not found
- 404 if file doesn't exist on disk
- 403 if user lacks permission
- 429 if rate limit exceeded

#### Frontend Implementation
**File**: `operator-dashboard/src/api/deliverables.ts`

```typescript
async download(deliverableId: string) {
  const response = await apiClient.get(
    `/api/deliverables/${deliverableId}/download`,
    { responseType: 'blob' }
  );
  // Trigger browser download
  const blob = new Blob([response.data]);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename; // Extract from Content-Disposition header
  link.click();
}
```

**File**: `operator-dashboard/src/pages/Deliverables.tsx`

```typescript
const handleDownload = async (deliverable: Deliverable) => {
  try {
    setDownloading(deliverable.id);
    await deliverablesApi.download(deliverable.id);
  } catch (error) {
    // Show error toast
  } finally {
    setDownloading(null);
  }
};

// Update button onClick
<button onClick={() => handleDownload(d)}>
  <Download className="h-3 w-3" />
  Download
</button>
```

**Testing**:
- Unit test: API function
- Integration test: Download triggers correctly
- E2E test: File downloads successfully

---

### 2. Actual File Size Calculation

#### Backend Implementation
**File**: `backend/services/crud.py`

```python
import os
from pathlib import Path

def get_deliverable_with_size(db: Session, deliverable_id: str) -> Optional[dict]:
    """Get deliverable with calculated file size"""
    deliverable = get_deliverable(db, deliverable_id)
    if not deliverable:
        return None

    # Calculate actual file size
    file_path = Path("data/outputs") / deliverable.path
    size_bytes = file_path.stat().st_size if file_path.exists() else 0

    return {
        **deliverable.__dict__,
        "size_bytes": size_bytes,
        "size_display": format_file_size(size_bytes)
    }

def format_file_size(bytes: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"
```

#### Database Schema Update
**File**: `backend/models/deliverable.py`

```python
class Deliverable(Base):
    # ... existing fields ...
    file_size_bytes = Column(Integer)  # Store actual size
```

**Migration**: Add migration to calculate and store sizes for existing deliverables

#### Frontend Update
**File**: `operator-dashboard/src/types/domain.ts`

```typescript
export const DeliverableSchema = z.object({
  // ... existing fields ...
  fileSizeBytes: z.number().optional(),
  fileSizeDisplay: z.string().optional(),
});
```

Remove mock `getFileSize()` function from `Deliverables.tsx` and use actual values from API.

---

### 3. Enhanced Deliverable Drawer

#### Backend Enhancement
**File**: `backend/routers/deliverables.py`

```python
@router.get("/{deliverable_id}/details", response_model=DeliverableDetailResponse)
async def get_deliverable_details(
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get deliverable with related content preview"""
    # Get deliverable
    # Get associated posts
    # Get QA report summary
    # Get file preview (first 1000 chars for text files)
    # Get download history
    # Return comprehensive details
```

**Schema**: `backend/schemas/deliverable.py`

```python
class DeliverableDetailResponse(DeliverableResponse):
    """Extended deliverable response with details"""
    file_preview: Optional[str] = None
    post_count: Optional[int] = None
    qa_summary: Optional[dict] = None
    related_files: List[str] = []
    download_count: int = 0
    last_downloaded_at: Optional[datetime] = None
```

#### Frontend Enhancement
**File**: `operator-dashboard/src/components/deliverables/DeliverableDrawer.tsx`

Complete rewrite with tabs:

```typescript
<Tabs defaultValue="overview">
  <TabsList>
    <Tab value="overview">Overview</Tab>
    <Tab value="preview">Preview</Tab>
    <Tab value="posts">Posts</Tab>
    <Tab value="qa">Quality</Tab>
    <Tab value="history">History</Tab>
  </TabsList>

  <TabPanel value="overview">
    {/* Metadata, status, dates, proof */}
  </TabPanel>

  <TabPanel value="preview">
    {/* File content preview (syntax highlighted for .md) */}
  </TabPanel>

  <TabPanel value="posts">
    {/* List of posts in this deliverable */}
  </TabPanel>

  <TabPanel value="qa">
    {/* QA report summary, quality scores */}
  </TabPanel>

  <TabPanel value="history">
    {/* Download history, delivery timeline */}
  </TabPanel>
</Tabs>
```

**Dependencies to Add**:
- `@radix-ui/react-tabs` (if not already installed)
- Syntax highlighter for preview (e.g., `react-syntax-highlighter`)

---

## Priority 1: High Priority Features

### 4. Email Delivery System

#### Backend Implementation

**File**: `backend/services/email_service.py` (new file)

```python
from typing import Optional
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

class EmailService:
    """Email service for sending deliverables"""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send_deliverable_email(
        self,
        to_email: str,
        client_name: str,
        deliverable_path: Path,
        cc_emails: Optional[List[str]] = None,
        message: Optional[str] = None,
    ):
        """Send deliverable via email with attachment"""
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = to_email
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        msg['Subject'] = f"Your Content Deliverable - {client_name}"

        # Email body (use template from agent/email_system.py)
        body = message or self._get_default_template(client_name)
        msg.attach(MIMEText(body, 'html'))

        # Attach file
        with open(deliverable_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), Name=deliverable_path.name)
            attachment['Content-Disposition'] = f'attachment; filename="{deliverable_path.name}"'
            msg.attach(attachment)

        # Send
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            recipients = [to_email] + (cc_emails or [])
            server.sendmail(self.username, recipients, msg.as_string())
```

**File**: `backend/routers/deliverables.py`

```python
@router.post("/{deliverable_id}/email")
async def email_deliverable(
    deliverable_id: str,
    request: EmailDeliverableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    email_service: EmailService = Depends(get_email_service),
):
    """Send deliverable via email"""
    deliverable = crud.get_deliverable(db, deliverable_id)
    if not deliverable:
        raise HTTPException(404, "Deliverable not found")

    # Send email
    await email_service.send_deliverable_email(
        to_email=request.to_email,
        client_name=deliverable.client.name,
        deliverable_path=Path("data/outputs") / deliverable.path,
        cc_emails=request.cc_emails,
        message=request.message,
    )

    # Log email sent in audit trail
    # Optionally mark as delivered

    return {"message": "Email sent successfully"}
```

**Schema**: `backend/schemas/deliverable.py`

```python
class EmailDeliverableRequest(BaseModel):
    """Request to email deliverable"""
    to_email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    cc_emails: Optional[List[str]] = None
    message: Optional[str] = None
    mark_as_delivered: bool = True
```

**Configuration**: `backend/config.py`

```python
class Settings(BaseSettings):
    # ... existing ...
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_NAME: str = "Content Jumpstart"
```

#### Frontend Implementation

**File**: `operator-dashboard/src/api/deliverables.ts`

```typescript
async email(deliverableId: string, input: EmailDeliverableInput) {
  const { data } = await apiClient.post(
    `/api/deliverables/${deliverableId}/email`,
    input
  );
  return data;
}
```

**File**: `operator-dashboard/src/components/deliverables/EmailDialog.tsx` (new)

```typescript
interface EmailDialogProps {
  deliverable: Deliverable | null;
  onClose: () => void;
  onSubmit: (input: EmailDeliverableInput) => void;
}

export function EmailDialog({ deliverable, onClose, onSubmit }: EmailDialogProps) {
  const [toEmail, setToEmail] = useState('');
  const [ccEmails, setCcEmails] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [markAsDelivered, setMarkAsDelivered] = useState(true);

  // Form with email inputs, CC, custom message, checkbox for mark as delivered
  // Preview of email template
  // Send button
}
```

**File**: `operator-dashboard/src/pages/Deliverables.tsx`

Add email dialog and button handler:

```typescript
const [selectedForEmail, setSelectedForEmail] = useState<Deliverable | null>(null);

const emailMutation = useMutation({
  mutationFn: (input: EmailDeliverableInput) => {
    if (!selectedForEmail) throw new Error('No deliverable selected');
    return deliverablesApi.email(selectedForEmail.id, input);
  },
  onSuccess: () => {
    // Show success toast
    // Refresh deliverables list
    // Close dialog
  },
});
```

---

### 5. Bulk Download (ZIP)

#### Backend Implementation

**File**: `backend/routers/deliverables.py`

```python
from fastapi.responses import StreamingResponse
import zipfile
import io

@router.post("/bulk-download")
async def bulk_download_deliverables(
    request: BulkDownloadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download multiple deliverables as ZIP"""
    deliverables = [
        crud.get_deliverable(db, id)
        for id in request.deliverable_ids
    ]

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for deliverable in deliverables:
            file_path = Path("data/outputs") / deliverable.path
            if file_path.exists():
                zip_file.write(file_path, arcname=file_path.name)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=deliverables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        }
    )
```

#### Frontend Implementation

**File**: `operator-dashboard/src/pages/Deliverables.tsx`

Add multi-select functionality:

```typescript
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

// Checkbox column in table
<td className="px-4 py-3">
  <input
    type="checkbox"
    checked={selectedIds.has(d.id)}
    onChange={() => toggleSelection(d.id)}
  />
</td>

// Bulk actions toolbar
{selectedIds.size > 0 && (
  <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-white shadow-lg rounded-lg p-4">
    <span>{selectedIds.size} selected</span>
    <button onClick={handleBulkDownload}>Download All (ZIP)</button>
    <button onClick={handleBulkEmail}>Email All</button>
    <button onClick={() => setSelectedIds(new Set())}>Clear</button>
  </div>
)}
```

---

### 6. Delete/Archive Functionality

#### Backend Implementation

**File**: `backend/models/deliverable.py`

```python
class Deliverable(Base):
    # ... existing fields ...
    deleted_at = Column(DateTime(timezone=True))
    archived = Column(Boolean, default=False)
```

**File**: `backend/routers/deliverables.py`

```python
@router.delete("/{deliverable_id}")
async def delete_deliverable(
    deliverable_id: str,
    permanent: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete or permanently delete deliverable"""
    if permanent:
        # Only allow for admin users
        # Actually delete file and DB record
        crud.delete_deliverable_permanent(db, deliverable_id)
    else:
        # Soft delete (set deleted_at)
        crud.soft_delete_deliverable(db, deliverable_id)
```

---

## Priority 2: Medium Priority Features

### 7. Advanced Filtering & Sorting

#### Backend Enhancement
Add query parameters to list endpoint:

```python
@router.get("/", response_model=List[DeliverableResponse])
async def list_deliverables(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    format: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    delivered_after: Optional[datetime] = None,
    delivered_before: Optional[datetime] = None,
    sort_by: str = "created_at",  # created_at, delivered_at, size, path
    sort_order: str = "desc",  # asc, desc
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List deliverables with advanced filters and sorting"""
```

#### Frontend Enhancement
Add filter controls:

```typescript
<DateRangePicker
  label="Created Date Range"
  value={createdDateRange}
  onChange={setCreatedDateRange}
/>

<Select
  label="Sort By"
  value={sortBy}
  onChange={setSortBy}
  options={[
    { value: 'created_at', label: 'Created Date' },
    { value: 'delivered_at', label: 'Delivered Date' },
    { value: 'file_size_bytes', label: 'File Size' },
    { value: 'path', label: 'Name' },
  ]}
/>
```

---

### 8. Track All Output Files

#### Current Situation
Each generation creates ~12 files but only main deliverable is tracked.

#### Proposed Solution

**Option A**: Track each file as separate deliverable
- Pros: Full tracking, individual download
- Cons: Clutters UI (12 entries per run)

**Option B**: Single deliverable with related files array
- Pros: Clean UI, grouped files
- Cons: Can't individually track downloads

**Recommended**: **Option B** with enhancement

**Database Schema**:

```python
class Deliverable(Base):
    # ... existing ...
    is_primary = Column(Boolean, default=True)
    parent_deliverable_id = Column(String, ForeignKey("deliverables.id"))

    # Relationships
    related_files = relationship("Deliverable", back_populates="parent")
    parent = relationship("Deliverable", remote_side=[id])
```

**Implementation**:
- Primary deliverable = main .md or .docx file
- Related files = all other files from same run
- UI shows primary with expandable section for related files
- Download button for primary
- "Download All" button for primary + related (ZIP)

---

## Priority 3: Nice to Have

### 9. Analytics Dashboard

Create new tab or section showing:
- Total deliverables over time (line chart)
- Deliverables by client (bar chart)
- Average time from creation to delivery
- Most downloaded deliverables
- Delivery success rate

**Implementation**: Use existing audit trail + new metrics table

---

### 10. Cloud Storage Integration

**Current**: Local file storage in `data/outputs/`
**Proposed**: AWS S3, Google Cloud Storage, or Azure Blob

**Benefits**:
- Scalability
- Backups
- CDN integration
- Signed URLs for secure download

**Implementation**:
- Add storage abstraction layer
- Configure storage backend via env vars
- Migrate existing files
- Update file serving to use storage URLs

---

## Implementation Timeline

### Week 1: Critical Features
- Day 1-2: File download (backend + frontend)
- Day 3: File size calculation
- Day 4-5: Enhanced drawer

### Week 2: High Priority
- Day 1-2: Email system
- Day 3: Bulk download
- Day 4-5: Delete/archive

### Week 3: Medium Priority
- Day 1-2: Advanced filtering
- Day 3-4: Track all output files
- Day 5: Testing and bug fixes

### Week 4: Polish & Deploy
- Day 1-2: Nice-to-have features (if time)
- Day 3-4: Comprehensive testing
- Day 5: Documentation and deployment

---

## Technical Dependencies

### Backend Dependencies
```
# requirements.txt additions (if needed)
python-multipart  # For file uploads (if needed)
aiosmtplib        # Async SMTP client (alternative to smtplib)
```

### Frontend Dependencies
```json
// package.json additions
{
  "@radix-ui/react-tabs": "^1.0.4",
  "react-syntax-highlighter": "^15.5.0",
  "date-fns": "^2.30.0"  // Already installed
}
```

### Environment Variables
```env
# .env additions
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_NAME=Content Jumpstart

# Optional: Cloud storage
STORAGE_BACKEND=local  # local, s3, gcs, azure
AWS_S3_BUCKET=your-bucket
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

---

## Database Migrations

### Migration 1: Add file size
```sql
ALTER TABLE deliverables ADD COLUMN file_size_bytes INTEGER;
UPDATE deliverables SET file_size_bytes = 0;  -- Will be calculated
```

### Migration 2: Add deletion tracking
```sql
ALTER TABLE deliverables ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE deliverables ADD COLUMN archived BOOLEAN DEFAULT FALSE;
```

### Migration 3: Add related files support
```sql
ALTER TABLE deliverables ADD COLUMN is_primary BOOLEAN DEFAULT TRUE;
ALTER TABLE deliverables ADD COLUMN parent_deliverable_id VARCHAR REFERENCES deliverables(id);
CREATE INDEX idx_deliverables_parent ON deliverables(parent_deliverable_id);
```

### Migration 4: Add download tracking
```sql
CREATE TABLE deliverable_downloads (
    id VARCHAR PRIMARY KEY,
    deliverable_id VARCHAR REFERENCES deliverables(id),
    user_id VARCHAR REFERENCES users(id),
    downloaded_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR,
    user_agent TEXT
);
CREATE INDEX idx_downloads_deliverable ON deliverable_downloads(deliverable_id);
CREATE INDEX idx_downloads_user ON deliverable_downloads(user_id);
```

---

## Testing Strategy

### Unit Tests
- `test_deliverable_download()` - Download endpoint
- `test_file_size_calculation()` - Size calculation
- `test_email_service()` - Email sending
- `test_bulk_download()` - ZIP creation
- `test_soft_delete()` - Deletion logic

### Integration Tests
- `test_download_flow()` - Full download flow
- `test_email_flow()` - Email delivery flow
- `test_mark_delivered_after_email()` - Auto-mark logic

### E2E Tests
- Download deliverable via UI
- Email deliverable via UI
- Bulk download multiple deliverables
- Filter and sort deliverables
- View drawer with all tabs

### Performance Tests
- Download large files (>10MB)
- Bulk download 50+ files
- List 1000+ deliverables with filters

---

## Risk Mitigation

### Risk 1: Large File Downloads
**Mitigation**:
- Use streaming responses
- Add file size limits (warn for >50MB)
- Implement resumable downloads (future)

### Risk 2: Email Delivery Failures
**Mitigation**:
- Retry logic (3 attempts)
- Queue failed emails for manual review
- Log all attempts
- Show clear error messages

### Risk 3: ZIP Memory Usage
**Mitigation**:
- Limit bulk download to 100 files max
- Show warning for large selections
- Use streaming ZIP creation (future)

### Risk 4: File Path Security
**Mitigation**:
- Validate all paths with `isSafeRelativePath()`
- Never trust user input for paths
- Audit log all file accesses
- Implement rate limiting

---

## Success Metrics

### Functional Metrics
- ✅ Users can download deliverables (100% success rate)
- ✅ Email delivery >95% success rate
- ✅ Bulk operations work for up to 100 items
- ✅ Drawer loads in <500ms
- ✅ File sizes accurate to within 1KB

### Performance Metrics
- Response time for list endpoint: <200ms (p95)
- Download initiation: <100ms
- Email send: <3s
- ZIP creation for 10 files: <2s

### User Experience Metrics
- Reduced manual email sending by 80%
- Reduced support tickets about downloads
- Increased operator efficiency (less time spent per deliverable)

---

## Conclusion

This plan prioritizes **immediate value** (downloads, file sizes) while building toward **complete functionality** (email, bulk operations). Each feature is designed to integrate with existing architecture and follow established patterns.

**Next Step**: Begin implementation with Phase 3 (Code).
