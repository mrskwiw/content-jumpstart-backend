# Revision Management System

## Overview

The Revision Management System tracks client revision requests, enforces scope limits (5 revisions per project), and provides intelligent post regeneration based on client feedback. This protects business margins while delivering excellent customer service.

## Business Context

**Problem**: Unlimited revisions destroy profitability. A $1,800 project with 10+ revision rounds can drop effective hourly rate from $300/hr to $90/hr.

**Solution**: Formal revision tracking with:
- 5-revision scope limit (included in base price)
- Automatic upsell trigger at limit
- Intelligent feedback parsing
- Change tracking and diff reports
- Client history for repeat customers

## Architecture

### Database Schema

```
projects
├── project_id (PK)
├── client_name
├── deliverable_path
├── num_posts
├── quality_profile_name
└── status

revisions
├── revision_id (PK)
├── project_id (FK)
├── attempt_number (1-10)
├── feedback
├── status
├── created_at
└── completed_at

revision_posts
├── revision_id (FK)
├── post_index (1-30)
├── template_id
├── original_content
├── original_word_count
├── revised_content
├── revised_word_count
└── changes_summary

revision_scope
├── project_id (PK, FK)
├── allowed_revisions (default: 5)
├── used_revisions
├── remaining_revisions (computed)
├── scope_exceeded (bool)
├── upsell_offered (bool)
└── upsell_accepted (bool)
```

### Data Models

**Project**: Represents a completed 30-post deliverable
```python
Project(
    project_id="AcmeAgency_20250101_120000",
    client_name="Acme Marketing Agency",
    deliverable_path="data/projects/AcmeAgency/deliverable.md",
    num_posts=30,
    quality_profile_name="professional_linkedin",
    status=ProjectStatus.COMPLETED
)
```

**Revision**: Tracks a single revision request
```python
Revision(
    revision_id="AcmeAgency_20250101_120000_rev_1",
    project_id="AcmeAgency_20250101_120000",
    attempt_number=1,
    feedback="Make posts 3, 7, and 12 more casual",
    status=RevisionStatus.PENDING,
    posts=[]  # Populated after generation
)
```

**RevisionScope**: Enforces limits
```python
scope = RevisionScope(
    project_id="AcmeAgency_20250101_120000",
    allowed_revisions=5,
    used_revisions=2
)
# Properties:
scope.remaining_revisions  # 3
scope.is_at_limit          # False
scope.is_near_limit        # False (becomes True when remaining == 1)
```

**RevisionPost**: Individual revised post
```python
RevisionPost(
    post_index=3,
    template_id=1,
    template_name="Problem Recognition",
    original_content="Original post...",
    original_word_count=250,
    revised_content="Revised post...",
    revised_word_count=230,
    changes_summary="Made tone more casual; shortened by 20 words"
)
```

## Database Layer Usage

### Initialize Database
```python
from src.database.project_db import ProjectDatabase

db = ProjectDatabase()  # Uses data/projects.db
# Or specify custom path:
db = ProjectDatabase(db_path=Path("custom.db"))
```

### Create Project
```python
from src.models.project import Project, ProjectStatus

project = Project(
    project_id="AcmeAgency_20250101_120000",
    client_name="Acme Marketing Agency",
    deliverable_path="data/projects/AcmeAgency/deliverable.md",
    brief_path="data/briefs/acme_brief.txt",
    num_posts=30,
    quality_profile_name="professional_linkedin",
    status=ProjectStatus.COMPLETED
)

db.create_project(project)
```

### Check Revision Scope
```python
scope = db.get_revision_scope("AcmeAgency_20250101_120000")

print(f"Allowed: {scope.allowed_revisions}")
print(f"Used: {scope.used_revisions}")
print(f"Remaining: {scope.remaining_revisions}")
print(f"At limit: {scope.is_at_limit}")
```

### Create Revision
```python
from src.models.project import Revision, RevisionStatus

revision = Revision(
    revision_id="AcmeAgency_20250101_120000_rev_1",
    project_id="AcmeAgency_20250101_120000",
    attempt_number=1,
    feedback="Make posts 3, 7, and 12 more casual and add emojis",
    status=RevisionStatus.PENDING
)

db.create_revision(revision)
# Scope automatically increments: used_revisions = 1
```

### Save Revised Posts
```python
from src.models.project import RevisionPost

posts = [
    RevisionPost(
        post_index=3,
        template_id=1,
        template_name="Problem Recognition",
        original_content="Original...",
        original_word_count=250,
        revised_content="Revised...",
        revised_word_count=230,
        changes_summary="Made tone more casual; shortened by 20 words"
    )
]

db.save_revision_posts(revision.revision_id, posts)
```

### Handle Upsell
```python
# Check if at limit
scope = db.get_revision_scope(project_id)
if scope.is_at_limit:
    db.mark_upsell_offered(project_id)
    # Present upsell to client...

# If client accepts:
db.accept_upsell(project_id, additional_revisions=5)
# Now: allowed_revisions = 10, scope_exceeded = False
```

### Query Client History
```python
# Get all projects for a client
projects = db.get_projects_by_client("Acme Marketing Agency")

# Get all revisions for a project
revisions = db.get_revisions_by_project("AcmeAgency_20250101_120000")

# Get client statistics
stats = db.get_client_stats("Acme Marketing Agency")
# Returns:
# {
#     "total_projects": 3,
#     "total_revisions": 8,
#     "avg_revisions_per_project": 2.67,
#     "scope_exceeded_count": 1
# }
```

## RevisionAgent Usage

### Generate Revised Post
```python
from src.agents.revision_agent import RevisionAgent
from src.models.post import Post
from src.models.client_brief import ClientBrief
from src.models.template import Template

agent = RevisionAgent()

revised_post, changes_summary = agent.generate_revised_post(
    original_post=original_post,
    client_feedback="Make this more casual and add an emoji",
    client_brief=client_brief,
    template=template
)

print(f"Changes: {changes_summary}")
# Output: "Made tone more casual; Added 1 emoji(s)"
```

### Intelligent Feedback Parsing

The RevisionAgent automatically detects common patterns:

| Client Says | Agent Detects | Generated Instruction |
|-------------|---------------|----------------------|
| "more casual" | Tone change | Make tone more casual (use contractions, shorter sentences) |
| "too long" / "shorter" | Length adjustment | Reduce length while keeping core message |
| "add emoji" | Emoji request | Include 1-2 relevant emojis |
| "more data" / "add stats" | Data request | Include specific statistics or data points |
| "add CTA" | CTA missing | Add a clear call-to-action or question at the end |
| "more professional" | Tone change | Make tone more professional (avoid contractions) |
| "add example" | Story request | Add a concrete example or personal story |
| "simpler" | Complexity | Simplify language and sentence structure |

### Batch Revision
```python
posts_to_revise = [post_3, post_7, post_12]

revised_results = agent.revise_multiple_posts(
    posts=posts_to_revise,
    client_feedback="Make all of these more casual",
    client_brief=client_brief,
    templates=template_library
)

for revised_post, changes in revised_results:
    print(f"Post #{revised_post.variant}: {changes}")
```

### Create Revision Diff
```python
diff = agent.create_revision_diff(
    original=original_post,
    revised=revised_post,
    changes_summary=changes_summary
)

print(diff.to_markdown())
```

Output:
```markdown
### Post #3: Problem Recognition

**Length:** 250 → 230 words (-20 words)

**Changes Made:**
- Made tone more casual
- Shortened by 20 words
- Added 1 emoji(s)

**Quality Improvement:** 80%
```

## CLI Commands

### Revise Posts
```bash
python 03_post_generator.py revise \
    --project "AcmeAgency_20250101_120000" \
    --posts "3,7,12" \
    --feedback "Make these more casual and add emojis"
```

### Check Scope Status
```bash
python 03_post_generator.py scope-status --project "AcmeAgency_20250101_120000"
```

Output:
```
Revision Scope Status
=====================
Project: AcmeAgency_20250101_120000
Client: Acme Marketing Agency

Revisions Used: 2 / 5
Remaining: 3

Status: Within scope ✓
```

### List Revisions
```bash
python 03_post_generator.py list-revisions --client "Acme Marketing Agency"
```

### Generate Diff Report
```bash
python 03_post_generator.py diff-report --revision "AcmeAgency_20250101_120000_rev_1"
```

## Workflow Examples

### Standard Revision Workflow

1. **Client requests changes**:
   ```
   "Posts 5, 12, and 18 need to be more casual.
   Also, post 12 is too long - can you shorten it?"
   ```

2. **Check scope**:
   ```python
   scope = db.get_revision_scope(project_id)
   if scope.is_at_limit:
       # Trigger upsell
   ```

3. **Create revision**:
   ```python
   revision = Revision(
       revision_id=f"{project_id}_rev_{scope.used_revisions + 1}",
       project_id=project_id,
       attempt_number=scope.used_revisions + 1,
       feedback=client_feedback
   )
   db.create_revision(revision)
   ```

4. **Generate revised posts**:
   ```python
   revised_posts = []
   for post_index in [5, 12, 18]:
       original_post = load_post(post_index)
       revised, changes = agent.generate_revised_post(
           original_post=original_post,
           client_feedback=client_feedback,
           client_brief=client_brief,
           template=get_template(original_post.template_id)
       )
       revised_posts.append(revised)
   ```

5. **Save and deliver**:
   ```python
   db.save_revision_posts(revision.revision_id, revised_posts)
   db.update_revision_status(revision.revision_id, RevisionStatus.COMPLETED)

   # Generate diff report
   generate_diff_report(revision.revision_id)
   ```

### Upsell Workflow

When client hits limit:

```python
scope = db.get_revision_scope(project_id)

if scope.is_at_limit and not scope.upsell_offered:
    db.mark_upsell_offered(project_id)

    message = f"""
    You've used all 5 included revisions.

    Additional revision rounds available:
    - 5 more revisions: $500
    - 10 more revisions: $900 (10% discount)
    - Unlimited revisions for this project: $1,200

    Would you like to add more revisions?
    """
    send_to_client(message)

# If client accepts:
if client_accepts:
    db.accept_upsell(project_id, additional_revisions=5)
    # Continue with revision...
```

## Scope Enforcement

### Validation Logic

```python
def can_create_revision(project_id: str) -> Tuple[bool, str]:
    """Check if revision can be created"""
    scope = db.get_revision_scope(project_id)

    if scope.is_at_limit:
        if scope.upsell_offered and not scope.upsell_accepted:
            return False, "Upsell pending. Awaiting client decision."
        elif not scope.upsell_offered:
            return False, "Revision limit reached. Offer upsell."

    return True, "OK"
```

### Warning Messages

```python
scope = db.get_revision_scope(project_id)

if scope.is_near_limit:
    print(f"⚠️  Warning: Only {scope.remaining_revisions} revision remaining")

if scope.is_at_limit:
    print("🛑 Revision limit reached. Additional revisions require purchase.")
```

## Analytics & Reporting

### Client Statistics
```python
stats = db.get_client_stats("Acme Marketing Agency")

print(f"Total Projects: {stats['total_projects']}")
print(f"Total Revisions: {stats['total_revisions']}")
print(f"Avg Revisions/Project: {stats['avg_revisions_per_project']}")
print(f"Scope Exceeded Count: {stats['scope_exceeded_count']}")
```

### Revision Summary Report
```python
summary = db.get_revision_summary()

for project in summary:
    print(f"{project['client_name']}: {project['revision_count']} revisions")
```

### Performance Metrics

Track these KPIs:
- **Avg revisions per project** - Target: 2-3 (indicates good discovery)
- **Scope exceeded rate** - Target: <20% (most clients stay within limit)
- **Upsell conversion** - Target: 40-50% accept additional revisions
- **Revenue per project** - Base + upsell revenue

## Best Practices

### Discovery Phase
- Detailed client brief reduces revision requests
- Voice sample analysis improves tone matching
- Clear CTA preferences prevent generic endings

### Setting Expectations
- Communicate 5-revision limit in proposal
- Explain "revision = batch of changes" (not per post)
- Position as quality assurance, not restriction

### Handling Scope Creep
- **In scope**: "Make post 7 more casual" ✓
- **Out of scope**: "Rewrite all 30 posts for Twitter" ✗
- **Out of scope**: "Add 10 new posts on different topics" ✗

### Upsell Messaging
- Frame as investment in perfection
- Offer bundled pricing (10 revisions cheaper than 5+5)
- Suggest annual retainer for ongoing content

## Testing

Run the comprehensive test suite:

```bash
cd project
python tests/test_revision_db.py
```

Tests cover:
1. Database initialization
2. Project creation
3. Revision scope tracking
4. Revision creation with scope updates
5. Revised posts storage
6. Scope limit enforcement
7. Upsell acceptance workflow
8. Client statistics queries

All tests should pass with `[OK]` status.

## Troubleshooting

### "Database locked" errors
- Ensure no concurrent writes
- Use context manager properly
- Close connections in `finally` blocks

### Scope not updating
- Check foreign key constraints
- Verify project exists before creating revision
- Confirm SQL trigger logic

### RevisionAgent failures
- Check API key configuration
- Verify client brief has required fields
- Ensure template structure is valid
- Review prompt construction in debug mode

## Future Enhancements

Planned features:
- **Client memory**: Store client preferences across projects
- **Voice fingerprinting**: Automatically calibrate tone from sample posts
- **Predictive analytics**: Identify clients likely to need revisions
- **Automated diff reports**: Email with visual before/after
- **Multi-client dashboards**: Agency view of all client revision status
