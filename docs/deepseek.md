# DeepSeek API Integration with Claude Code

## Executive Summary

**Claude Code does NOT natively support DeepSeek or any non-Anthropic models.** The only workaround is deploying a LiteLLM proxy server to translate between API formats, which comes with significant limitations and is not officially supported.

---

## 1. The Reality

### What Claude Code Supports Natively

| Provider | Supported | Configuration |
|----------|-----------|---------------|
| Anthropic API | Yes | Default |
| Amazon Bedrock | Yes | `CLAUDE_CODE_USE_BEDROCK=1` |
| Google Vertex AI | Yes | `CLAUDE_CODE_USE_VERTEX=1` |
| Microsoft Foundry | Yes | Azure configuration |
| **DeepSeek** | **No** | Not supported |
| **OpenAI** | **No** | Not supported |
| **Any OpenAI-compatible** | **No** | Not supported |

### Why DeepSeek Won't Work Directly

Claude Code requires one of these API formats:
- Anthropic Messages format (`/v1/messages`)
- Bedrock InvokeModel format
- Vertex rawPredict format

DeepSeek provides an **OpenAI-compatible API**, which Claude Code **cannot use directly**.

```
DeepSeek API (OpenAI format)
         │
         X ── Claude Code cannot parse this format
         │
Claude Code expects Anthropic format
```

---

## 2. LiteLLM Proxy Workaround

The only path to using DeepSeek is deploying LiteLLM as a translation proxy.

### Architecture

```
┌─────────────┐     Anthropic      ┌─────────────┐     OpenAI       ┌─────────────┐
│ Claude Code │ ──── format ────►  │   LiteLLM   │ ──── format ───► │  DeepSeek   │
│             │ ◄─────────────────  │   Proxy     │ ◄────────────── │    API      │
└─────────────┘                    └─────────────┘                  └─────────────┘
```

### Requirements

1. **Server to host LiteLLM** (local or cloud)
2. **DeepSeek API key** from [platform.deepseek.com](https://platform.deepseek.com)
3. **Technical knowledge** to configure and maintain proxy

### Step 1: Install LiteLLM

```bash
pip install litellm[proxy]
```

### Step 2: Create LiteLLM Configuration

Create `litellm_config.yaml`:

```yaml
model_list:
  # Map Claude model names to DeepSeek
  - model_name: claude-sonnet-4-5-20241022
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY

  - model_name: claude-opus-4-5-20251101
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY

  # For subagents using Haiku
  - model_name: claude-haiku-3-5-20241022
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY

litellm_settings:
  drop_params: true  # Drop unsupported params instead of erroring
```

### Step 3: Run LiteLLM Proxy

```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key"
litellm --config litellm_config.yaml --port 4000
```

### Step 4: Configure Claude Code

Option A: Environment variables
```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_API_KEY=sk-1234  # LiteLLM accepts any key by default
```

Option B: Settings file (`.claude/settings.json`)
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_API_KEY": "sk-placeholder"
  }
}
```

### Step 5: Test

```bash
claude --version
# Should connect to LiteLLM proxy
```

---

## 3. Critical Limitations

### Features That Will NOT Work

| Feature | Why It Fails |
|---------|--------------|
| **Prompt caching** | Anthropic-specific, DeepSeek doesn't support |
| **Extended context (200K)** | DeepSeek max is 64K-128K |
| **Tool use fidelity** | Different function calling format |
| **Vision/images** | DeepSeek-chat doesn't support images |
| **Streaming responses** | May have compatibility issues |
| **Beta features** | Headers not forwarded properly |

### GCR-ABM Specific Concerns

| Task | Risk Level | Issue |
|------|------------|-------|
| Code exploration | Medium | May miss context in large files |
| Multi-file edits | High | Tool use differences may cause errors |
| Complex reasoning | High | DeepSeek quality differs from Claude |
| Agent subprocesses | High | Model switching may break |

### Model Quality Differences

DeepSeek vs Claude for GCR-ABM tasks:

| Capability | Claude Opus | DeepSeek Chat |
|------------|-------------|---------------|
| Complex reasoning | Excellent | Good |
| Code generation | Excellent | Good |
| Following specs | Excellent | Moderate |
| Context handling | 200K tokens | 64K-128K tokens |
| Tool use | Native | Emulated |
| Consistency | High | Variable |

---

## 4. DeepSeek Free Tier Details

### What DeepSeek Offers

| Aspect | Value |
|--------|-------|
| Free tier | Yes (limited) |
| Rate limits | Lower than paid |
| Models | deepseek-chat, deepseek-coder |
| Context window | 64K (chat), 128K (coder) |
| API format | OpenAI-compatible |

### Pricing (if you exceed free tier)

| Model | Input | Output |
|-------|-------|--------|
| deepseek-chat | $0.14/M tokens | $0.28/M tokens |
| deepseek-coder | $0.14/M tokens | $0.28/M tokens |

**Comparison**: Claude Opus is ~$15/$75 per M tokens - DeepSeek is ~100x cheaper.

---

## 5. Alternative Approaches

### Option A: Use DeepSeek Directly (Not via Claude Code)

For tasks that don't require Claude Code's tooling:

```python
# direct_deepseek.py
from openai import OpenAI

client = OpenAI(
    api_key="your-deepseek-key",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Analyze this code..."}]
)
```

### Option B: Hybrid Approach

Use Claude Code for complex tasks, DeepSeek for simple ones:

```bash
# Complex tasks: Claude Code (Anthropic API)
claude "Review the CQE implementation against Chen paper"

# Simple tasks: Direct DeepSeek script
python ask_deepseek.py "Explain what this function does" < gcr_model.py
```

### Option C: Wait for Official Support

Anthropic may add more providers in the future. Currently no roadmap for OpenAI-compatible endpoints.

---

## 6. If You Proceed with LiteLLM

### Monitoring

Add logging to track issues:

```yaml
# litellm_config.yaml additions
litellm_settings:
  success_callback: ["langfuse"]  # Optional: external logging

general_settings:
  master_key: sk-your-admin-key
```

### Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "Invalid model" | Model name mismatch | Check litellm_config.yaml mapping |
| "Tool use failed" | Format incompatibility | Set `drop_params: true` |
| Timeout errors | DeepSeek rate limits | Add retry logic or reduce concurrency |
| Garbled responses | Streaming issues | Disable streaming in LiteLLM |

### Health Check

```bash
# Test LiteLLM is running
curl http://localhost:4000/health

# Test model endpoint
curl http://localhost:4000/v1/models
```

---

## 7. Recommendation

### For GCR-ABM Development

**Do NOT use DeepSeek for this project.** Reasons:

1. **BoE audit context** - Using unofficial/unsupported tooling undermines credibility
2. **Complex codebase** - 1,700+ line simulation needs reliable tool use
3. **Context requirements** - Chen paper + code + docs exceeds DeepSeek limits
4. **Quality requirements** - Financial model needs high reasoning accuracy

### When DeepSeek Might Be Acceptable

- Personal experimentation
- Simple code tasks
- Cost-sensitive hobby projects
- Tasks under 64K context

### Budget-Conscious Alternative

If Anthropic API costs are a concern:
1. Use Claude Haiku for exploration tasks (10x cheaper than Opus)
2. Set `/model sonnet` for most work (3x cheaper than Opus)
3. Reserve Opus for complex reasoning tasks only

```bash
/model haiku    # Cheap exploration
/model sonnet   # Standard work
/model opus     # Complex analysis only
```

---

## 8. Summary

| Question | Answer |
|----------|--------|
| Can I use DeepSeek with Claude Code? | Not directly |
| Is there a workaround? | LiteLLM proxy (unsupported) |
| Should I use it for GCR-ABM? | No - too risky for BoE audit context |
| Is it cheaper? | Yes, ~100x cheaper |
| Is it reliable? | No - many features won't work |
| Official Anthropic support? | None - "use at your own discretion" |

---

## Appendix: Quick Setup Script (If You Still Want to Try)

```bash
#!/bin/bash
# setup_deepseek_proxy.sh - USE AT YOUR OWN RISK

# Install LiteLLM
pip install litellm[proxy]

# Create config
cat > litellm_config.yaml << 'EOF'
model_list:
  - model_name: claude-sonnet-4-5-20241022
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY

litellm_settings:
  drop_params: true
EOF

# Set your key
export DEEPSEEK_API_KEY="your-key-here"

# Run proxy
litellm --config litellm_config.yaml --port 4000 &

# Configure Claude Code
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_API_KEY=sk-placeholder

# Test
claude --version
```

**Warning**: This is unsupported and will likely break various Claude Code features.

---

*Document Version: 1.0*
*Created: 2026-01-04*
*Status: Informational - NOT RECOMMENDED for GCR-ABM*
