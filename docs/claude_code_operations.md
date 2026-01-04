# Claude Code Operations Guide for GCR-ABM

## Executive Summary

This document covers the operational management of Claude Code for the GCR-ABM simulation project, including API licensing, agent management, cost monitoring, and failure scenarios.

**Critical Point**: Claude Code uses API authentication exclusively. There is NO fallback to a chat license if tokens run out.

---

## 1. API Licensing vs Chat License

### 1.1 How Claude Code Authentication Works

| Aspect | Claude Code (API) | Claude Chat (Web) |
|--------|-------------------|-------------------|
| Authentication | API key via Console | Web login |
| Billing | Per-token usage | Subscription ($20/mo Pro) |
| Rate Limits | TPM/RPM quotas | Conversation limits |
| Fallback | None | N/A |
| Workspace | Dedicated "Claude Code" workspace | N/A |

**Key Understanding**: These are completely separate systems. Your Claude Pro/Team chat subscription does NOT provide API tokens for Claude Code, and Claude Code cannot fall back to chat.

### 1.2 What Happens When API Tokens Run Out

```
API Quota Exhausted
        │
        ▼
┌─────────────────────────────────────────┐
│  Claude Code receives HTTP 429 or       │
│  billing error from API                 │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  Session fails with error message       │
│  NO automatic fallback occurs           │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  Options:                               │
│  1. Wait for quota window reset         │
│  2. Request higher limits               │
│  3. Switch cloud provider (Bedrock/     │
│     Vertex) if configured               │
└─────────────────────────────────────────┘
```

**Error Messages You May See**:
- `Rate limit exceeded` (HTTP 429)
- `Billing limit reached`
- `Insufficient quota`

**There is NO**:
- Automatic downgrade to smaller model
- Fallback to chat interface
- Graceful degradation

### 1.3 Setting Spend Limits

To prevent unexpected costs, configure spend limits in Claude Console:

1. Log into [console.anthropic.com](https://console.anthropic.com)
2. Navigate to Workspace Settings > Billing
3. Set monthly spend limit (requires Admin role)
4. When limit reached, API calls are denied (hard stop)

---

## 2. Agent Management

### 2.1 Built-in Subagents

Claude Code includes these subagent types for the GCR-ABM project:

| Subagent | Purpose | Tools | Model |
|----------|---------|-------|-------|
| `general-purpose` | Complex multi-step tasks | All | Inherited |
| `Explore` | Codebase search and analysis | Read-only | Haiku (fast) |
| `Plan` | Implementation planning | Read-only | Inherited |
| `claude-code-guide` | Documentation lookup | Read-only | Inherited |

### 2.2 Creating Custom Agents

Custom agents for GCR-ABM can be created in `.claude/agents/`:

```yaml
# .claude/agents/gcr-validator.md
---
name: gcr-validator
description: Validates GCR simulation outputs against Chen paper specifications
model: sonnet
tools:
  - Read
  - Grep
  - Glob
  - Bash(python3 -c:*)
---

You are a validation agent for the GCR-ABM simulation. Your role is to:
1. Compare simulation outputs against Chen (2025) specifications
2. Verify economic constraints are properly enforced
3. Check climate physics calculations

Reference documents:
- docs/chen_chap5.md (authoritative specification)
- docs/climate.md (climate model design)
```

### 2.3 Agent File Locations

| Location | Scope | Priority |
|----------|-------|----------|
| `.claude/agents/` | Project-specific | Highest |
| `~/.claude/agents/` | User (all projects) | Lower |

### 2.4 Managing Agents via CLI

```bash
# List available agents
/agents

# View agent permissions
/permissions

# Check agent status during operation
# (agents return unique agentId for resumption)
```

---

## 3. Verifying Agent Operation

### 3.1 In-Session Verification

**Check Current Cost and Usage**:
```bash
/cost
```

Output example:
```
Total cost:            $2.45
Total duration (API):  12m 33.2s
Total duration (wall): 45m 10.8s
Total code changes:    156 lines added, 23 lines removed
```

**Check Model in Use**:
```bash
/model
```

**View Active Permissions**:
```bash
/permissions
```

### 3.2 Agent Execution Tracking

When subagents run, they return an `agentId`:
```
agentId: a03c126 (for resuming to continue this agent's work if needed)
```

This ID allows:
- Resuming interrupted agent work
- Tracking which agent performed which actions
- Debugging agent behavior

### 3.3 Verification Checklist for GCR-ABM

| Check | Command | Expected |
|-------|---------|----------|
| Model active | `/model` | `opus` or configured model |
| Permissions set | `/permissions` | Python, git permissions listed |
| Cost tracking | `/cost` | Non-zero if work performed |
| Agent available | `/agents` | Lists built-in + custom agents |

---

## 4. Monitoring API Usage and Costs

### 4.1 Real-Time Monitoring

**Session Cost**:
```bash
/cost
```

**Typical Usage for GCR-ABM**:
- Simple query: $0.01-0.05
- Code exploration: $0.10-0.50
- Major refactoring: $1.00-5.00
- Full simulation review: $2.00-10.00

### 4.2 Console Monitoring

1. Log into [console.anthropic.com](https://console.anthropic.com)
2. View Usage dashboard for:
   - Daily/monthly token consumption
   - Cost breakdown by model
   - Rate limit status

### 4.3 OpenTelemetry Monitoring (Advanced)

For production/team deployments, enable telemetry:

```bash
# Add to .claude/settings.json or environment
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**Key Metrics**:
| Metric | Description |
|--------|-------------|
| `claude_code.cost.usage` | Cost per session (USD) |
| `claude_code.token.usage` | Tokens by type |
| `claude_code.session.count` | Sessions started |
| `claude_code.lines_of_code.count` | Code modifications |

### 4.4 Cost Estimates for GCR-ABM Work

| Task Type | Estimated Cost | Tokens |
|-----------|---------------|--------|
| Read simulation output | $0.02-0.10 | 5k-20k |
| Explore codebase | $0.20-0.50 | 50k-100k |
| Design document creation | $0.50-2.00 | 100k-300k |
| Full code review | $2.00-5.00 | 300k-800k |
| Major refactoring | $5.00-15.00 | 800k-2M |

**Monthly Budget Recommendation**: $100-200 for active development

---

## 5. Failure Scenarios and Recovery

### 5.1 API Quota Exhausted

**Symptoms**:
- Error message about rate limits
- Claude Code stops responding
- HTTP 429 errors in logs

**Recovery**:
1. Wait for quota window reset (typically hourly/daily)
2. Check Console for current usage vs limits
3. Request limit increase if recurring

### 5.2 Spend Limit Reached

**Symptoms**:
- Billing error messages
- All API calls rejected

**Recovery**:
1. Log into Console
2. Increase spend limit (requires Admin)
3. Or wait for next billing period

### 5.3 Network/API Outage

**Symptoms**:
- Connection timeout errors
- API unavailable messages

**Recovery**:
1. Check [status.anthropic.com](https://status.anthropic.com)
2. Wait for service restoration
3. Consider Bedrock/Vertex as backup provider

### 5.4 Context Window Exhausted

**Symptoms**:
- Claude Code auto-compacts conversation
- Earlier context lost

**Recovery**:
- Use `/compact` with custom instructions to preserve key context
- Start new session with `/clear`
- Reference key files explicitly

---

## 6. Best Practices for GCR-ABM Development

### 6.1 Cost Optimization

1. **Use Explore agent for searches** - Uses Haiku (cheaper/faster)
2. **Be specific in queries** - Avoid broad "explain everything"
3. **Use `/compact` between major tasks** - Reduces context size
4. **Reference files directly** - Don't ask Claude to "find" known files

### 6.2 Session Management

```bash
# Start fresh for new task
/clear

# Compact when context large
/compact Focus on: climate model, CQE logic, inflation constraints

# Check cost periodically
/cost
```

### 6.3 Recommended Workflow

```
1. Start session
2. Define specific task
3. Let Claude work (uses subagents as needed)
4. Check /cost periodically
5. /compact if context grows large
6. /clear between unrelated tasks
```

---

## 7. Configuration for This Project

### 7.1 Current Settings

Your `.claude/settings.json` includes:

```json
{
  "model": "opus",
  "permissions": {
    "allow": [
      "Bash(python gcr_model.py:*)",
      "Bash(python3:*)",
      "Bash(pip3 install:*)",
      "Bash(venv/bin/pip install:*)",
      "Bash(venv/bin/python:*)",
      "Bash(git add:*)",
      "Bash(git push:*)"
    ]
  }
}
```

### 7.2 Recommended Additions

```json
{
  "model": "opus",
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1"
  },
  "permissions": {
    "allow": [
      "Bash(python gcr_model.py:*)",
      "Bash(python3:*)",
      "Bash(pytest:*)",
      "Bash(venv/bin/python:*)",
      "Bash(venv/bin/pytest:*)",
      "Bash(git:*)"
    ]
  }
}
```

### 7.3 Custom Agent for Validation

Create `.claude/agents/gcr-audit.md`:

```yaml
---
name: gcr-audit
description: Audit GCR simulation against Chen paper and BoE requirements
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---

You are an auditor for the GCR-ABM simulation. Compare implementation against:
1. Chen (2025) specification in docs/chen_chap5.md
2. Climate model design in docs/climate.md
3. CQE Gold Pool model in docs/cqe_gold_pool_model.md

Report discrepancies with specific line references.
```

---

## 8. Summary: Key Points for BoE Audit Context

| Concern | Reality | Mitigation |
|---------|---------|------------|
| API token exhaustion | Hard failure, no fallback | Set spend limits, monitor usage |
| Chat license fallback | Does NOT exist | Ensure adequate API budget |
| Agent verification | agentId tracking, /cost command | Regular monitoring |
| Cost control | Per-token billing | Console spend limits |
| Operational continuity | Depends on API availability | Consider Bedrock/Vertex backup |

**Bottom Line**: Claude Code is an API-based tool with usage-based billing. Plan for adequate API budget and monitoring. There is no "safety net" of falling back to a chat subscription.

---

## Appendix: Quick Reference Commands

| Command | Purpose |
|---------|---------|
| `/cost` | Show session cost and usage |
| `/model` | Show/change current model |
| `/permissions` | View allowed operations |
| `/agents` | List available subagents |
| `/compact` | Reduce context size |
| `/clear` | Start fresh session |
| `/help` | Full command list |

---

*Document Version: 1.0*
*Created: 2026-01-04*
*Applies to: Claude Code with Anthropic API*
