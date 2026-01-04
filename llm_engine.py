"""
LLM Engine - Core infrastructure for LLM-powered agents in GCR-ABM simulation

Provides:
- LLMEngine: Unified interface for local LLM (Ollama) with caching
- DecisionCache: SQLite-based caching for reproducibility
- CacheMode: Enum for cache behavior control
"""

import json
import hashlib
import sqlite3
import logging
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class CacheMode(Enum):
    """Cache behavior modes for LLM decisions"""
    DISABLED = "disabled"       # No caching, always call LLM
    READ_WRITE = "read_write"   # Check cache first, store new decisions
    READ_ONLY = "read_only"     # Use cache only, error on miss
    WRITE_ONLY = "write_only"   # Always call LLM, store results


@dataclass
class LLMDecision:
    """Structured LLM decision with metadata"""
    agent: str
    year: int
    state_hash: str
    decision: Dict[str, Any]
    reasoning: str
    model: str
    timestamp: str
    run_id: str = ""


class DecisionCache:
    """SQLite-based decision caching for reproducibility and audit trail"""

    def __init__(self, db_path: str = "llm_decisions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                year INTEGER,
                agent TEXT,
                state_hash TEXT,
                decision TEXT,
                reasoning TEXT,
                model TEXT,
                timestamp TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lookup
            ON decisions(state_hash, agent)
        """)
        conn.commit()
        conn.close()

    def store(self, decision: LLMDecision):
        """Store a decision in the cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO decisions
            (run_id, year, agent, state_hash, decision, reasoning, model, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.run_id,
            decision.year,
            decision.agent,
            decision.state_hash,
            json.dumps(decision.decision),
            decision.reasoning,
            decision.model,
            decision.timestamp
        ))
        conn.commit()
        conn.close()

    def retrieve(self, state_hash: str, agent: str) -> Optional[LLMDecision]:
        """Retrieve a cached decision by state hash and agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT run_id, year, agent, state_hash, decision, reasoning, model, timestamp
            FROM decisions
            WHERE state_hash = ? AND agent = ?
            ORDER BY id DESC
            LIMIT 1
        """, (state_hash, agent))
        row = cursor.fetchone()
        conn.close()

        if row:
            return LLMDecision(
                run_id=row[0],
                year=row[1],
                agent=row[2],
                state_hash=row[3],
                decision=json.loads(row[4]),
                reasoning=row[5],
                model=row[6],
                timestamp=row[7]
            )
        return None

    def clear(self):
        """Clear all cached decisions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM decisions")
        conn.commit()
        conn.close()

    def export_decisions(self, path: str, run_id: Optional[str] = None):
        """Export decisions to JSON for audit trail"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if run_id:
            cursor.execute("""
                SELECT run_id, year, agent, state_hash, decision, reasoning, model, timestamp
                FROM decisions WHERE run_id = ?
                ORDER BY year, agent
            """, (run_id,))
        else:
            cursor.execute("""
                SELECT run_id, year, agent, state_hash, decision, reasoning, model, timestamp
                FROM decisions ORDER BY run_id, year, agent
            """)

        rows = cursor.fetchall()
        conn.close()

        decisions = []
        for row in rows:
            decisions.append({
                "run_id": row[0],
                "year": row[1],
                "agent": row[2],
                "state_hash": row[3],
                "decision": json.loads(row[4]),
                "reasoning": row[5],
                "model": row[6],
                "timestamp": row[7]
            })

        with open(path, 'w') as f:
            json.dump(decisions, f, indent=2)

        return len(decisions)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM decisions")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT agent, COUNT(*) FROM decisions GROUP BY agent")
        by_agent = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(DISTINCT run_id) FROM decisions")
        runs = cursor.fetchone()[0]

        conn.close()

        return {
            "total_decisions": total,
            "by_agent": by_agent,
            "total_runs": runs
        }


class LLMEngine:
    """Unified LLM interface with caching support for Ollama"""

    def __init__(self,
                 model: str = "llama3.2",
                 cache_mode: CacheMode = CacheMode.READ_WRITE,
                 cache_path: str = "llm_decisions.db",
                 run_id: Optional[str] = None,
                 timeout: int = 60):
        """
        Initialize LLM Engine

        Args:
            model: Ollama model name (llama3.2, mistral, deepseek-r1:8b, etc.)
            cache_mode: Caching behavior (DISABLED, READ_WRITE, READ_ONLY, WRITE_ONLY)
            cache_path: Path to SQLite cache database
            run_id: Unique identifier for this simulation run
            timeout: Request timeout in seconds
        """
        self.model = model
        self.cache_mode = cache_mode
        self.timeout = timeout
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize cache if needed
        if cache_mode != CacheMode.DISABLED:
            self.cache = DecisionCache(cache_path)
        else:
            self.cache = None

        # Check Ollama availability
        self._ollama_available = self._check_ollama()
        if not self._ollama_available:
            logger.warning("Ollama not available. LLM agents will use rule-based fallback.")

    def _check_ollama(self) -> bool:
        """Check if Ollama is available and model is pulled"""
        try:
            import ollama
            # Try to list models to verify connection
            models = ollama.list()
            available_models = [m['name'].split(':')[0] for m in models.get('models', [])]
            if self.model.split(':')[0] not in available_models:
                logger.warning(f"Model {self.model} not found. Available: {available_models}")
                logger.warning(f"Run: ollama pull {self.model}")
                return False
            return True
        except ImportError:
            logger.warning("ollama package not installed. Run: pip install ollama")
            return False
        except Exception as e:
            logger.warning(f"Ollama connection failed: {e}")
            return False

    def _hash_state(self, state: Dict[str, Any]) -> str:
        """Create deterministic hash of state for caching"""
        # Sort keys for deterministic hashing
        state_str = json.dumps(state, sort_keys=True, default=str)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API and return response"""
        import ollama

        response = ollama.chat(
            model=self.model,
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            options={
                'temperature': 0.3,  # Lower temperature for more consistent decisions
                'num_predict': 500   # Limit response length
            }
        )

        return response['message']['content']

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code blocks"""
        # Try to find JSON in response
        text = response.strip()

        # Handle markdown code blocks
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            text = text[start:end].strip()
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            text = text[start:end].strip()

        # Find JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            text = text[start:end]

        return json.loads(text)

    def decide(self,
               agent_name: str,
               prompt_template: str,
               state: Dict[str, Any],
               year: int = 0) -> Dict[str, Any]:
        """
        Make a decision using LLM with caching

        Args:
            agent_name: Name of the agent making the decision
            prompt_template: Prompt template with {placeholders}
            state: State dictionary to fill template and hash
            year: Current simulation year

        Returns:
            Dictionary with decision fields (agent-specific)

        Raises:
            RuntimeError: If LLM unavailable and cache miss in READ_ONLY mode
        """
        state_hash = self._hash_state(state)

        # Check cache first (if enabled)
        if self.cache_mode in (CacheMode.READ_WRITE, CacheMode.READ_ONLY):
            cached = self.cache.retrieve(state_hash, agent_name)
            if cached:
                logger.debug(f"Cache hit for {agent_name} at year {year}")
                return cached.decision

        # Cache miss in READ_ONLY mode is an error
        if self.cache_mode == CacheMode.READ_ONLY:
            raise RuntimeError(f"Cache miss for {agent_name} in READ_ONLY mode")

        # Check if Ollama is available
        if not self._ollama_available:
            raise ConnectionError("Ollama not available")

        # Format prompt with state
        prompt = prompt_template.format(**state)

        # Call LLM
        try:
            response_text = self._call_ollama(prompt)
            decision = self._parse_json_response(response_text)

            # Extract reasoning if present
            reasoning = decision.pop('reasoning', response_text[:200])

            # Store in cache (if enabled)
            if self.cache_mode in (CacheMode.READ_WRITE, CacheMode.WRITE_ONLY):
                llm_decision = LLMDecision(
                    agent=agent_name,
                    year=year,
                    state_hash=state_hash,
                    decision=decision,
                    reasoning=reasoning,
                    model=self.model,
                    timestamp=datetime.now().isoformat(),
                    run_id=self.run_id
                )
                self.cache.store(llm_decision)

            logger.debug(f"LLM decision for {agent_name}: {decision}")
            return decision

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM call failed for {agent_name}: {e}")
            raise

    @property
    def is_available(self) -> bool:
        """Check if LLM is available for decisions"""
        return self._ollama_available

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {"cache": "disabled"}

    def export_audit_trail(self, path: str) -> int:
        """Export all decisions for this run to JSON"""
        if self.cache:
            return self.cache.export_decisions(path, self.run_id)
        return 0


# Convenience function for testing
def test_llm_engine():
    """Test LLM engine with a simple prompt"""
    engine = LLMEngine(model="llama3.2", cache_mode=CacheMode.DISABLED)

    if not engine.is_available:
        print("Ollama not available. Please install and run Ollama:")
        print("  curl -fsSL https://ollama.com/install.sh | sh")
        print("  ollama pull llama3.2")
        return False

    test_prompt = """
    You are testing an LLM integration.

    Current value: {value}

    Respond with JSON only:
    {{"result": "success", "doubled": {doubled}}}
    """

    state = {"value": 21, "doubled": 42}

    try:
        result = engine.decide("test", test_prompt, state)
        print(f"LLM Engine test passed: {result}")
        return True
    except Exception as e:
        print(f"LLM Engine test failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_llm_engine()
