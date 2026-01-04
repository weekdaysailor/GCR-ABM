# LLM-Powered Agents for GCR-ABM Simulation

## Overview

The GCR-ABM simulation supports LLM-powered agents that use local language models (via Ollama) to make decisions instead of rule-based logic. This enables more realistic and adaptive agent behavior while maintaining zero API costs.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GCR_ABM_Simulation                           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │     CEA     │  │ CentralBank │  │  Investor   │             │
│  │   (LLM)     │  │   (LLM)     │  │   (LLM)     │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                   ┌──────▼──────┐                               │
│                   │  LLMEngine  │                               │
│                   │  (Ollama)   │                               │
│                   └──────┬──────┘                               │
│                          │                                      │
│                   ┌──────▼──────┐                               │
│                   │DecisionCache│                               │
│                   │  (SQLite)   │                               │
│                   └─────────────┘                               │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  (Rule-based, unchanged)     │
│  │  Projects   │  │   Auditor   │                               │
│  │   Broker    │  │             │                               │
│  └─────────────┘  └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install Ollama

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve
```

### 2. Pull Required Models

```bash
# Fast model for most decisions
ollama pull llama3.2

# Better reasoning (optional)
ollama pull mistral

# Best reasoning for policy decisions (optional)
ollama pull deepseek-r1:8b
```

### 3. Install Python Dependencies

```bash
pip install ollama
# Or update requirements
pip install -r requirements.txt
```

## Usage

### Basic LLM Simulation

```python
from gcr_model import GCR_ABM_Simulation

# Run with LLM-powered agents
sim = GCR_ABM_Simulation(
    years=50,
    llm_enabled=True,
    llm_model="llama3.2",
    llm_cache_mode="read_write"
)

df = sim.run_simulation()
```

### Select Specific LLM Agents

```python
# Only use LLM for investor behavior
sim = GCR_ABM_Simulation(
    years=50,
    llm_enabled=True,
    llm_agents=["investor", "capital"]  # Others stay rule-based
)
```

### Monte Carlo with LLM Variation

```python
# Disable caching for stochastic variation
results = []
for i in range(100):
    sim = GCR_ABM_Simulation(
        years=50,
        llm_enabled=True,
        llm_cache_mode="disabled"
    )
    results.append(sim.run_simulation())
```

### Reproducible Validation Runs

```python
# Cache mode ensures identical results
sim = GCR_ABM_Simulation(
    years=50,
    llm_enabled=True,
    llm_cache_mode="read_write"  # Cache decisions for reproducibility
)
```

## LLM Agents

### InvestorMarketLLM

Replaces mechanical sentiment decay/recovery with LLM reasoning about investor psychology.

**Decision**: New sentiment value (0.1 to 1.0)

**Inputs**:
- CO2 level and change
- Inflation vs target
- CEA warnings
- Previous sentiment
- Market price vs floor

**Reasoning**: "Is the system making progress? Are economic constraints manageable?"

### CapitalMarketLLM

Replaces formula-based capital flows with LLM reasoning about investor behavior.

**Decision**: Net capital flow as % of market cap (-10% to +10%)

**Inputs**:
- Market cap and price
- CO2 progress toward target
- Inflation hedge demand
- Investor sentiment

**Reasoning**: "Forward-looking investors care about climate trajectory..."

### CEA_LLM

Uses LLM for periodic policy reviews (every 5 years) while maintaining rule-based logic between reviews.

**Decision**: Warning flag, brake factor, floor direction

**Inputs**:
- Stability ratio
- Inflation vs target
- CO2 vs roadmap
- Budget utilization

**Reasoning**: Per Chen (2025) GCR specification...

### CentralBankAllianceLLM

Reasons about intervention strategy when defending the XCR price floor.

**Decision**: Intervention percentage (0-100% of gap to close)

**Inputs**:
- Price gap below floor
- Inflation level
- Budget remaining
- Year of simulation

**Reasoning**: "Over-intervention signals desperation, under-intervention risks credibility..."

## Cache Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `disabled` | Always call LLM, no caching | Monte Carlo variation |
| `read_write` | Check cache first, store new | Reproducible runs |
| `read_only` | Use cache only, error on miss | Strict reproducibility |
| `write_only` | Always call LLM, store results | Warm cache |

## Decision Cache

All LLM decisions are stored in SQLite (`llm_decisions.db`) for:
- Reproducibility
- Audit trail
- Performance analysis

### Export Decisions

```python
# Export all decisions for audit
engine = sim.llm_engine
engine.export_audit_trail("decisions_audit.json")
```

### Cache Schema

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    run_id TEXT,
    year INTEGER,
    agent TEXT,
    state_hash TEXT,
    decision JSON,
    reasoning TEXT,
    model TEXT,
    timestamp TEXT
);
```

## Model Recommendations

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `llama3.2` | 3B | Fast | Good | InvestorMarket, CapitalMarket |
| `mistral` | 7B | Medium | Better | CEA, CentralBank |
| `deepseek-r1:8b` | 8B | Medium | Best | Complex policy reasoning |
| `phi3` | 3.8B | Fast | Good | Lightweight alternative |

## Fallback Behavior

All LLM agents automatically fall back to rule-based logic if:
- Ollama is not running
- Model is not pulled
- LLM returns invalid JSON
- Timeout or connection error

```python
# This always works, even without Ollama
sim = GCR_ABM_Simulation(llm_enabled=True)
# Falls back gracefully with warning message
```

## Performance

| Configuration | Time per Year | Cost |
|---------------|---------------|------|
| Rule-based only | ~0.1 seconds | Free |
| LLM (llama3.2) | ~2-5 seconds | Free |
| LLM (mistral) | ~5-10 seconds | Free |
| LLM (cached) | ~0.1 seconds | Free |

## Testing

```bash
# Run LLM agent tests
python test_llm_agents.py

# Expected output:
# LLM AGENT TEST SUITE
# ✓ Cache Operations
# ✓ InvestorMarket Fallback
# ✓ CapitalMarket Fallback
# ...
```

## Files

| File | Purpose |
|------|---------|
| `llm_engine.py` | LLMEngine class, DecisionCache, CacheMode |
| `llm_agents.py` | LLM-powered agent subclasses |
| `test_llm_agents.py` | Test suite |
| `llm_decisions.db` | SQLite decision cache (auto-created) |

## Limitations

1. **Local LLM Quality**: Local models (3-8B parameters) have lower reasoning quality than cloud models (Claude, GPT-4)

2. **Latency**: Each LLM decision adds ~2-10 seconds. Use caching for repeated runs.

3. **Non-Determinism**: LLM outputs vary slightly. Use temperature=0.3 and caching for consistency.

4. **Context Window**: Local models have limited context (~4K-8K tokens). Prompts are kept concise.

## Future Improvements

1. **Multi-model routing**: Use faster model for simple decisions, better model for complex ones

2. **Fine-tuning**: Train models on GCR-specific scenarios for better reasoning

3. **Cloud API option**: Optional cloud model integration for higher quality (with cost)

4. **Dashboard integration**: Show LLM reasoning in dashboard for transparency
