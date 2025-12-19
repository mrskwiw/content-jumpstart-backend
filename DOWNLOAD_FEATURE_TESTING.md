# Download Feature Testing Guide

## Feature: File Download Functionality
**Implementation Date**: 2025-12-19
**Commit**: `981356a`

---

## What Was Implemented

### Backend
- **Endpoint**: `GET /api/deliverables/{deliverable_id}/download`
- **Security**: Path validation, prevents directory traversal attacks
- **File Types**: Supports txt, md, docx, pdf, json, csv, xlsx, ics
- **Headers**: Proper Content-Disposition for browser downloads

### Frontend
- **API Method**: `deliverablesApi.download(id)`
- **UI Integration**: Download buttons in grouped and list views
- **UX**: Loading states, error handling, visual feedback

---

## Testing Checklist

### Backend Testing

#### Unit Tests (To Be Created)
- [ ] Test download endpoint with valid deliverable ID
- [ ] Test with invalid deliverable ID (should return 404)
- [ ] Test with non-existent file (should return 404)
- [ ] Test path traversal attempt (should return 403)
- [ ] Test each supported file format
- [ ] Test Content-Disposition header extraction
- [ ] Test media type detection

#### Manual Backend Testing
```bash
# 1. Start backend server
cd backend
uvicorn main:app --reload --port 8000

# 2. Get deliverable list
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/deliverables

# 3. Download a deliverable (replace {id} with actual ID)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  -o downloaded_file.txt \
  http://localhost:8000/api/deliverables/{id}/download

# 4. Verify file was downloaded
ls -lh downloaded_file.txt
file downloaded_file.txt
```

### Frontend Testing

#### Manual UI Testing
1. **Setup**
   - [ ] Start backend: `uvicorn backend.main:app --reload --port 8000`
   - [ ] Start frontend: `cd operator-dashboard && npm run dev`
   - [ ] Navigate to http://localhost:5173/dashboard/deliverables
   - [ ] Login with credentials

2. **Test Download in Grouped View**
   - [ ] Locate a deliverable in grouped view
   - [ ] Click "Download" button
   - [ ] Verify button shows "Downloading..." with bouncing icon
   - [ ] Verify file downloads successfully
   - [ ] Verify correct filename
   - [ ] Verify file content is correct

3. **Test Download in List View**
   - [ ] Switch to "List" view
   - [ ] Click download icon button
   - [ ] Verify loading state (icon bounces)
   - [ ] Verify file downloads

4. **Test Multiple Downloads**
   - [ ] Download multiple files in succession
   - [ ] Verify each completes successfully
   - [ ] Verify no conflicts

5. **Test Different File Formats**
   - [ ] Download a .txt file
   - [ ] Download a .md file
   - [ ] Download a .docx file
   - [ ] Download a .json file
   - [ ] Download a .csv file
   - [ ] Verify each opens correctly

6. **Error Handling**
   - [ ] Test download with invalid ID (should show error alert)
   - [ ] Test download with deleted file (should show error)
   - [ ] Verify error message is user-friendly

7. **Loading States**
   - [ ] Verify button disables during download
   - [ ] Verify icon animates during download
   - [ ] Verify button re-enables after completion
   - [ ] Test clicking multiple download buttons rapidly

### Integration Testing

#### E2E Test Scenarios (To Be Created)
```typescript
describe('Deliverables Download', () => {
  it('should download a deliverable successfully', async () => {
    // Login
    // Navigate to deliverables page
    // Click download button
    // Verify file downloads
  });

  it('should handle download errors gracefully', async () => {
    // Mock API error
    // Click download
    // Verify error message shows
  });

  it('should show loading state during download', async () => {
    // Click download
    // Verify button disabled
    // Verify loading text
    // Wait for completion
  });
});
```

### Performance Testing

- [ ] Download small file (<1MB) - should be instant
- [ ] Download medium file (1-10MB) - should complete in <5s
- [ ] Download large file (>10MB) - should stream properly
- [ ] Test concurrent downloads (5+ files)
- [ ] Monitor network tab for proper streaming

### Security Testing

- [ ] Verify authentication required
- [ ] Test path traversal attempts: `../../etc/passwd`
- [ ] Test absolute paths: `/etc/passwd`
- [ ] Verify only files in data/outputs/ are accessible
- [ ] Test with user who doesn't own the deliverable
- [ ] Verify no information leakage in error messages

---

## Known Limitations

1. **No Toast Notifications**: Currently uses `alert()` for errors
   - Enhancement: Add toast notification system

2. **No Download History**: Downloads not tracked in audit log
   - Enhancement: Add download tracking table

3. **No Progress Indicator**: For large files
   - Enhancement: Add progress bar

4. **No Resume Support**: Downloads can't be resumed if interrupted
   - Enhancement: Implement resumable downloads

5. **No Bulk Download**: Can't download multiple files as ZIP yet
   - Enhancement: Feature #5 in roadmap

---

## Success Criteria

✅ **Minimum Viable**:
- Users can download any deliverable they have access to
- Files download with correct filenames
- Basic error handling works

✅ **Production Ready**:
- All file formats download correctly
- Security validation prevents unauthorized access
- Loading states provide clear feedback
- Errors are user-friendly
- Works in both view modes

🎯 **Ideal**:
- Download tracking/analytics
- Toast notifications instead of alerts
- Progress indicators for large files
- Bulk download support

---

## Deployment Checklist

### Pre-Deployment
- [ ] All manual tests pass
- [ ] Code reviewed
- [ ] No console errors
- [ ] Security review completed

### Deployment
- [ ] Backend deployed to Render
- [ ] Frontend built and deployed
- [ ] Environment variables verified
- [ ] Database migrations (if any) applied

### Post-Deployment
- [ ] Smoke test download on production
- [ ] Monitor error logs
- [ ] Check performance metrics
- [ ] Collect user feedback

---

## Quick Verification Commands

### Backend Health Check
```bash
# Test endpoint is registered
curl http://localhost:8000/docs | grep download

# Test with actual deliverable
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/deliverables/DELIVERABLE_ID/download \
  --output test.txt
```

### Frontend Build Check
```bash
cd operator-dashboard
npm run build
# Should build without errors
```

---

## Rollback Plan

If issues are found in production:

1. **Backend Issues**: Revert commit `981356a`
2. **Frontend Issues**: Deploy previous build
3. **Critical Bug**: Disable download button via feature flag (if implemented)

---

## Next Steps

After download feature is verified:

1. **Add File Size Calculation** (Feature #2)
   - Add actual file sizes to database
   - Remove mock file size function
   - Display real sizes in UI

2. **Enhanced Drawer** (Feature #3)
   - Add preview tab
   - Show related files
   - Display download history

3. **Email Delivery** (Feature #4)
   - SMTP integration
   - Email dialog component
   - Send deliverables via email
