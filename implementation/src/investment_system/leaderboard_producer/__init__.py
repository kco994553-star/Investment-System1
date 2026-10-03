"""REAL/RESEARCH Leaderboard producer.

Consumes persisted QGV company results and the existing LeaderboardEngine.
Does not invent a ranking formula, rescore QGV, or publish an Official leaderboard.
"""

from .rank import build_leaderboard

__all__ = ["build_leaderboard"]
