# Content Generation Agent - User Guide

**Version:** 2.0 (Week 2 Intelligence + Week 3 Polish)
**Last Updated:** December 2025

This guide covers the enhanced internal CLI agent for the 30-Day Content Jumpstart service, including all Week 2 intelligence features and Week 3 polish enhancements.

**New Reference:** Strategic service packaging and pricing lives in `../STRATEGY_SERVICE.md`.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Features](#core-features)
3. [Intelligence Features (Week 2)](#intelligence-features-week-2)
4. [Polish Features (Week 3)](#polish-features-week-3)
5. [Command Reference](#command-reference)
6. [Workflow Examples](#workflow-examples)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Start the agent:**
   ```bash
   python agent_cli_enhanced.py chat
   ```

### First Run

On first startup, you'll see:
- Welcome message with feature overview
- Proactive suggestions (if any pending items exist)
- Command prompt ready for input

---

## Core Features

### Interactive Chat

The agent understands natural language commands:

```
You: Generate posts for Acme Corp
Agent: I'll help you generate posts. Do you have a client brief ready?

You: Yes, it's in data/briefs/acme_brief.txt
Agent: [Reads brief and generates 30 posts]
```

### Tool Execution

The agent can execute various tools automatically:

- **generate_posts** - Generate 30 social media posts
- **collect_feedback** - Collect client feedback
- **collect_satisfaction** - Run satisfaction surveys
- **upload_voice_samples** - Analyze brand voice
- **show_dashboard** - Display analytics
- **process_revision** - Handle revision requests *(Week 3)*
- **generate_analytics_report** - Create reports *(Week 3)*
- **create_posting_schedule** - Schedule posts *(Week 3)*

### Context Awareness

The agent maintains conversation context:
- Remembers current client and project
- Tracks recent actions
- Suggests next steps based on workflow state

---

## Intelligence Features (Week 2)

### 1. Proactive Suggestions

The agent automatically detects and suggests actions for:

- **Missing Feedback** - Projects >2 weeks old without client feedback
- **Overdue Invoices** - Unpaid invoices >7 days past due
- **Pending Deliverables** - Completed content not yet sent
- **Client Milestones** - Anniversaries and achievement dates

**Example:**
```
💡 Proactive Suggestions:

┌─ Overdue Invoice: INV-001 ─────────────────┐
│ Client has an invoice 5 days overdue       │
│                                             │
│ Recommended Actions:                        │
│   1. Send reminder email                    │
│   2. Schedule follow-up call                │
└─────────────────────────────────────────────┘
```

**Commands:**
- Type `pending` or `daily summary` to see all suggestions
- Agent shows suggestions automatically on startup

### 2. Workflow Planning

Complex operations are planned before execution:

**Example - Onboarding Workflow:**
```
You: Onboard new client "StartupXYZ"

Agent:
📋 Workflow Plan

Intent: Onboard new client StartupXYZ
Total Steps: 5
Estimated Time: 45 minutes

Tasks:
  1. 📝 Create client brief (10 min)
  2. 🎤 Analyze voice samples (15 min)
  3. ✍️  Generate 30 posts (10 min)
  4. ✅ Quality check (5 min)
  5. 📧 Send deliverable (5 min)

Execute this workflow? [y/n]:
```

**Workflow Types:**
- **Onboarding** - Complete client setup
- **Batch Operations** - Process multiple pending items
- **Custom** - Single or multi-step operations

### 3. Error Recovery

Automatic retry with exponential backoff:

- **API Failures** - Retries up to 3 times with increasing delays
- **Timeouts** - Graceful handling with user notification
- **Rate Limits** - Waits and retries automatically

**Recovery Pattern:**
- Attempt 1: Immediate
- Attempt 2: 1 second delay
- Attempt 3: 2 second delay
- Attempt 4: 4 second delay

### 4. Task Scheduling

Schedule future tasks with natural language:

**Examples:**
```
You: Remind me tomorrow to follow up with ClientX
Agent: ✅ Scheduled reminder for December 4, 2025 at 9:00 AM

You: Send invoice reminder every week for overdue invoices
Agent: ✅ Scheduled weekly task (5 iterations max)
```

**Supported Frequencies:**
- `ONCE` - One-time execution
- `DAILY` - Every day
- `WEEKLY` - Every 7 days
- `BIWEEKLY` - Every 14 days
- `MONTHLY` - Every 30 days

**View scheduled tasks:**
```bash
python agent_cli_enhanced.py scheduled
```

### 5. Email Integration

Send emails directly from the agent:

**Email Types:**
- **DELIVERABLE** - Send completed content package
- **FEEDBACK_REQUEST** - Request client feedback
- **INVOICE_REMINDER** - Payment reminder
- **SATISFACTION_SURVEY** - Post-project survey
- **REVISION_CONFIRMATION** - Confirm revision completion

**Example:**
```
You: Send deliverable to client@acme.com for Acme Corp project

Agent:
📧 Email prepared:
   To: client@acme.com
   Subject: Your 30-Day Content Package is Ready
   Attachments: 3 files

Send now? [y/n]:
```

**Development Mode:**
- Without SMTP configured, emails are logged to `data/email_logs/`
- Perfect for testing without sending real emails

### 6. Batch Operations

Process multiple pending items at once:

**Example:**
```
You: Process all pending tasks

Agent:
📋 Batch Operations Plan

Found:
  - 3 pending feedback requests
  - 1 pending revision
  - 2 overdue invoices

Workflow Plan:
  1. Request feedback from Client A
  2. Request feedback from Client B
  3. Request feedback from Client C
  4. Process revision for Client D
  5. Send invoice reminder to Client E
  6. Send invoice reminder to Client F

Execute? [y/n]:
```

---

## Polish Features (Week 3)

### 1. Conversation History

Full conversation persistence with search and export:

**Save & Load:**
- All conversations automatically saved to SQLite database
- Resume any previous session with `--session <id>` flag
- Sessions tracked with timestamps and metadata

**Export to Markdown:**
```bash
python agent_cli_enhanced.py export -s <session_id>
```

Output example:
```markdown
# Conversation Export

**Session ID:** abc-123-def
**Created:** 2025-12-03 14:30:00
**Client:** Acme Corp
**Project:** Q4 Campaign

---

### User (14:30:15)
Generate posts for Acme Corp

---

### Agent (14:30:45)
I've generated 30 posts for Acme Corp...
```

**Search Conversations:**
```bash
# Search all messages
python agent_cli_enhanced.py search -s <session_id> "invoice"

# Search only user messages
python agent_cli_enhanced.py search -s <session_id> "feedback" -r user
```

**Get Summary:**
```bash
python agent_cli_enhanced.py summary -s <session_id>
```

Output:
```
Conversation Summary

Session ID: abc-123-def
Client: Acme Corp
Project: Q4 Campaign

Statistics:
  Total messages: 24
  User messages: 12
  Assistant messages: 12

Timeline:
  First message: 2025-12-03 14:30:00
  Last message: 2025-12-03 15:45:00
  Duration: 1 hour, 15 minutes
```

### 2. Rich Console Output

Enhanced visual presentation:

**Code Syntax Highlighting:**
```python
# Code blocks are displayed with:
# - Syntax highlighting
# - Line numbers
# - Language-specific coloring
# - Panel borders
```

**Tree Visualizations:**
```
📝 Tasks
├─ 📝 Create client brief (10 min)
├─ 🎤 Analyze voice samples (15 min)
│  └─ Dependencies:
│     → Create client brief
└─ ✍️  Generate 30 posts (10 min)
   └─ Dependencies:
      → Analyze voice samples
```

**Progress Bars:**
```
⠋ Processing workflow tasks... ━━━━━━━━━━━━━━━━━━ 60% 3/5
```

**Panels:**
```
┌─ Agent Response ────────────────────────────┐
│ I've successfully generated 30 posts for    │
│ Acme Corp based on their brand voice.       │
│                                              │
│ Next steps:                                  │
│   1. Review posts for quality                │
│   2. Send to client for feedback             │
└──────────────────────────────────────────────┘
```

### 3. Tool Wrappers

New tool wrappers added:

**Process Revision:**
```python
await agent.tools.process_revision(
    client_name="Acme Corp",
    project_id="proj_123",
    revision_notes="Make posts more technical",
    regenerate_count=5
)
```

**Generate Analytics Report:**
```python
report = agent.tools.generate_analytics_report(
    client_name="Acme Corp",
    report_type="summary"  # or "detailed"
)
```

**Create Posting Schedule:**
```python
schedule = agent.tools.create_posting_schedule(
    client_name="Acme Corp",
    project_id="proj_123",
    posts_per_week=4,
    start_date="2025-12-10"
)
```

---

## Command Reference

### Chat Commands

Inside the chat interface:

| Command | Description |
|---------|-------------|
| `help` | Show help message |
| `pending` | Show pending items and suggestions |
| `daily summary` | Same as `pending` |
| `scheduled` | Show upcoming scheduled tasks |
| `reset` | Clear conversation history (keeps session) |
| `new` | Start new session |
| `exit` | Save and quit |

### CLI Commands

From the command line:

```bash
# Start chat
python agent_cli_enhanced.py chat

# Resume previous session
python agent_cli_enhanced.py chat --session <session_id>

# Enable debug mode
python agent_cli_enhanced.py chat --debug

# List recent sessions
python agent_cli_enhanced.py sessions
python agent_cli_enhanced.py sessions --limit 20

# Show scheduled tasks
python agent_cli_enhanced.py scheduled

# Show pending items
python agent_cli_enhanced.py pending

# Export conversation
python agent_cli_enhanced.py export -s <session_id>
python agent_cli_enhanced.py export -s <session_id> -o custom_path.md

# Search conversation
python agent_cli_enhanced.py search -s <session_id> <query>
python agent_cli_enhanced.py search -s <session_id> "posts" -r user

# Get conversation summary
python agent_cli_enhanced.py summary -s <session_id>
```

---

## Workflow Examples

### Example 1: Complete Client Onboarding

```
You: I have a new client called "TechStartup" who needs content

Agent: Great! I'll help you onboard TechStartup. Let me plan the workflow.

[Displays workflow plan with 5 steps]

Execute this workflow? [y/n]: y

Agent:
⠋ Processing workflow tasks... ━━━━━━ 40% 2/5

[Completes workflow]

┌─ ✅ Workflow Complete! ─────────────┐
│ Completed: 5 tasks                  │
│ Failed: 0 tasks                     │
└─────────────────────────────────────┘

You: Send the deliverable to client@techstartup.com

Agent: [Sends email with attachments]
```

### Example 2: Handle Batch Operations

```
You: What needs my attention?

Agent:
💡 Proactive Suggestions:

┌─ Missing Feedback ──────────────────┐
│ 3 clients haven't provided feedback │
└─────────────────────────────────────┘

┌─ Overdue Invoices ──────────────────┐
│ 2 invoices are past due             │
└─────────────────────────────────────┘

You: Process all pending tasks

Agent: [Creates batch workflow with 5 tasks]

Execute this workflow? [y/n]: y

Agent: [Processes all tasks with progress bar]
```

### Example 3: Schedule Recurring Task

```
You: Every Monday at 9am, generate a weekly summary report

Agent: ✅ Scheduled recurring task:
  Description: Generate weekly summary report
  Frequency: Weekly (every Monday)
  Next execution: December 9, 2025 at 9:00 AM

You: Show me all scheduled tasks

Agent:
Upcoming Scheduled Tasks

Description              | Scheduled For  | Frequency | Status
-------------------------|----------------|-----------|--------
Weekly summary report    | In 6 days      | Weekly    | Pending
Follow up with ClientX   | Tomorrow 9am   | Once      | Pending
```

### Example 4: Search Past Conversations

```
# From CLI
$ python agent_cli_enhanced.py search -s abc-123 "invoice"

Found 3 message(s) matching 'invoice':

1. USER (14:32:15)
   Send invoice to client...

2. ASSISTANT (14:32:30)
   Invoice INV-001 has been sent to client@acme.com...

3. USER (15:10:05)
   Check status of invoice...
```

---

## Troubleshooting

### Common Issues

**1. "ANTHROPIC_API_KEY not found"**

**Solution:**
```bash
# Check .env file exists
ls .env

# Set API key
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

**2. "No module named 'agent'"**

**Solution:**
```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import agent; print('OK')"
```

**3. "Database is locked"**

**Solution:**
```bash
# Close other agent instances
# Or delete lock file
rm data/*.db-wal
```

**4. Tests failing**

**Solution:**
```bash
# Run tests with verbose output
python -m pytest tests/agent/test_week3_features.py -v

# Check for missing dependencies
pip install pytest pytest-asyncio
```

**5. Conversation history not persisting**

**Solution:**
- Check database exists: `ls data/agent_sessions.db`
- Verify messages are being saved (check debug logs)
- Try exporting: `python agent_cli_enhanced.py export -s <session_id>`

### Debug Mode

Enable debug logging:

```bash
# Start with debug flag
python agent_cli_enhanced.py chat --debug

# Check logs
cat logs/content_jumpstart.log
```

### Performance Issues

**Slow API responses:**
- Check internet connection
- Verify API key is valid
- Review rate limits in Anthropic console

**Database slow:**
- Check database size: `du -h data/agent_sessions.db`
- Vacuum database: `sqlite3 data/agent_sessions.db "VACUUM;"`
- Archive old sessions

### Getting Help

**Resources:**
- [Implementation Plan](../IMPLEMENTATION_PLAN.md)
- [Phase 9A Completion Docs](../PHASE_9A_WEEK2_COMPLETION.md)
- [Agent Architecture](../project/README.md)

**Contact:**
- Report issues in the project repository
- Check logs in `logs/` directory
- Review test failures for debugging clues

---

## Best Practices

### 1. Session Management

- Resume sessions for continuity: `--session <id>`
- Export important conversations for documentation
- Use descriptive session names when possible

### 2. Workflow Planning

- Review workflow plans before executing
- Use batch operations for efficiency
- Break complex tasks into smaller workflows

### 3. Error Handling

- Let automatic retry handle transient errors
- Check error logs for persistent issues
- Use debug mode when troubleshooting

### 4. Scheduling

- Set realistic execution times
- Limit recurring tasks to prevent overload
- Monitor scheduled tasks regularly

### 5. Email Integration

- Test with development mode first (no SMTP)
- Verify email content before sending
- Use templates for consistency

---

## Advanced Features

### Custom Tool Integration

Add your own tools by extending `AgentTools`:

```python
# agent/tools.py
async def custom_tool(self, param1: str) -> Dict[str, Any]:
    """Your custom tool implementation"""
    try:
        # Your logic here
        return {
            "success": True,
            "message": "Tool executed successfully",
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

### Workflow Customization

Create custom workflows in `agent/planner.py`:

```python
def plan_custom_workflow(self, **params) -> WorkflowPlan:
    """Plan your custom workflow"""
    tasks = [
        PlannedTask(
            task_id="task_1",
            description="Step 1",
            tool_name="tool_1",
            tool_params={"param": "value"},
            estimated_duration_seconds=60
        ),
        # Add more tasks...
    ]

    return WorkflowPlan(
        intent="Custom workflow",
        tasks=tasks,
        requires_confirmation=True
    )
```

---

## Version History

**v2.0 (Week 2 + Week 3)**
- ✅ Conversation history persistence
- ✅ Rich console output with syntax highlighting
- ✅ New tool wrappers (revision, analytics, schedule)
- ✅ Comprehensive integration tests
- ✅ User documentation

**v1.5 (Week 2 - Intelligence)**
- ✅ Proactive suggestions
- ✅ Workflow planning
- ✅ Error recovery with exponential backoff
- ✅ Task scheduling
- ✅ Email integration
- ✅ Batch operations

**v1.0 (Week 1 - Foundation)**
- ✅ Basic conversational agent
- ✅ Tool execution
- ✅ Context management
- ✅ Session persistence

---

**End of User Guide**
