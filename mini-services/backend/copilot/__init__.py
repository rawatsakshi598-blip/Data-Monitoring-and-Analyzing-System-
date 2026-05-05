"""
AI Data Prep Copilot — Chat-based data preparation assistant.

Provides conversational AI assistance for data preparation tasks including
transformation suggestions, quality rule recommendations, and ML preparation
guidance. Uses the project's LLM client with automatic fallback to heuristics.
"""

from copilot.engine import CopilotEngine

# Module-level singleton for convenience
_engine = None


def get_engine() -> CopilotEngine:
    """Get or create the shared CopilotEngine instance."""
    global _engine
    if _engine is None:
        _engine = CopilotEngine()
    return _engine


__all__ = ["CopilotEngine", "get_engine"]
