"""Two-sided judgement of a billing cycle against its cap.

The cap is paid for whether or not it is used, so finishing far below it
wastes money exactly as finishing above it does.

A cycle is on target when it lands inside the band running from
``target_pct`` of the cap up to the cap itself.
"""

import dataclasses
import math


@dataclasses.dataclass(frozen=True)
class Verdict:
    final_amount: float
    cap: float
    target_pct: float

    @property
    def target_gb(self) -> float:
        return self.cap * self.target_pct / 100.0

    @property
    def pct_of_cap(self) -> float:
        if self.cap <= 0:
            return 0.0
        return self.final_amount / self.cap * 100.0

    @property
    def unused_gb(self) -> float:
        return max(0.0, self.cap - self.final_amount)

    @property
    def is_over(self) -> bool:
        return self.final_amount > self.cap

    @property
    def is_under_target(self) -> bool:
        return self.final_amount < self.target_gb


def pace_band(
    current_amount: float,
    cap: float,
    target_pct: float,
    days: int,
) -> tuple[float, float] | None:
    """Daily usage that lands the cycle on the target floor and on the cap."""
    if days <= 0:
        return None
    floor = cap * target_pct / 100.0
    low = max(0.0, (floor - current_amount) / days)
    high = max(0.0, (cap - current_amount) / days)
    return low, high


def days_to_cap(current_amount: float, cap: float, avg: float) -> int | None:
    """Days of usage at ``avg`` still needed before the cap is reached."""
    if avg <= 0:
        return None
    remaining = cap - current_amount
    if remaining <= 0:
        return None
    return math.ceil(remaining / avg)
