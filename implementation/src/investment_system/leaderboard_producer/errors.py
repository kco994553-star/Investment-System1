"""Fail-closed errors. A Leaderboard PASS is not an investment conclusion."""


class LeaderboardProducerError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
