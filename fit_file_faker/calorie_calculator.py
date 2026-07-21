"""Estimate total calories for FIT activities missing the value.

Some bike computers (notably Hammerhead Karoo) record activity data without
populating `total_calories` in `SessionMessage`/`LapMessage`. When the file
is uploaded to Garmin Connect those activities show up with 0 kcal, which
breaks downstream calculations like daily totals and the nutrition module.

This module re-derives calories from per-record samples already present in
the file. Two methods are supported, in order of preference:

1. **Power-based** — integrate `RecordMessage.power` over time to get the
   total mechanical work in kJ, then convert to metabolic kcal assuming a
   gross efficiency of 22% (`1 kJ work × 1 / (0.22 × 4.184) ≈ 1.086 kcal`;
   see `_GROSS_EFFICIENCY`). No anthropometric input needed.

2. **HR-based fallback** — Keytel et al. (2005) regression on
   `RecordMessage.heart_rate`, requiring the rider's weight, age, and sex.

When the power method is selected but the meter drops out mid-activity, the
affected intervals are individually filled from heart rate (when the profile
provides the HR inputs) instead of counting zero work.

The chosen method, the session total, and a per-lap breakdown are returned
together so the editor can write them into both `SessionMessage` and the
individual `LapMessage` records.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from fit_file_faker.vendor.fit_tool.profile.messages.lap_message import LapMessage
from fit_file_faker.vendor.fit_tool.profile.messages.record_message import (
    RecordMessage,
)

_logger = logging.getLogger("garmin")

# Max gap between two consecutive samples that we still treat as "recording".
# Longer gaps are assumed to be pauses and are clamped to this value, so a
# pause contributes at most 30 s worth of energy at the resuming sample.
_MAX_SAMPLE_GAP_S = 30.0

# Minimum fraction of records that must carry a valid reading of the signal
# (power or heart rate) for the corresponding method to be chosen.
_COVERAGE_THRESHOLD = 0.5

# Plausibility bounds for individual samples. Devices often emit the FIT
# spec's "invalid uint16" marker (65535 for power, 255 for HR) when a
# sensor briefly drops out; fit_tool sometimes lets those through as real
# values. We also reject obviously absurd readings to keep the integral
# robust against single-sample spikes.
_POWER_MAX_W = 2000  # world-class sprinters peak ~2500W, anything beyond is noise
_HR_MIN_BPM = 30
_HR_MAX_BPM = 230

# Cyclist gross efficiency: ratio of mechanical work to metabolic energy.
# 22% is the de facto industry standard used by Hammerhead, Garmin Edge,
# Strava and most recreational-cycling tools (a small handful of training
# platforms use 24% which targets elite riders). Coyle et al. (1991) and
# Moseley & Jeukendrup (2001) report measured GE in the 20-25% range.
_GROSS_EFFICIENCY = 0.22
# Multiplier from kJ of mechanical work to kcal of metabolic expenditure:
#   kcal = J / GE / 4184 = kJ / (GE * 4.184)
# For GE = 0.22 this works out to ~1.0861.
_KJ_TO_KCAL = 1.0 / (_GROSS_EFFICIENCY * 4.184)


def _valid_power(p):
    return p is not None and 0 <= p <= _POWER_MAX_W


def _valid_hr(hr):
    return hr is not None and _HR_MIN_BPM <= hr <= _HR_MAX_BPM


def _has_hr_inputs(profile) -> bool:
    """Whether the profile carries everything the Keytel formula needs."""
    return (
        profile is not None
        and profile.weight_kg is not None
        and profile.age is not None
        and profile.sex in ("male", "female")
    )


@dataclass
class CalorieResult:
    """Outcome of a calorie estimation run."""

    total_calories: int
    per_lap_calories: list[int]
    method: str  # "power" | "hr" | "none"
    reason: str


def calculate_from_records(
    records: Sequence[RecordMessage],
    laps: Sequence[LapMessage],
    profile,
) -> CalorieResult:
    """Estimate session and per-lap calories from raw FIT records.

    Args:
        records: All `RecordMessage` instances from the file, in original
            order (assumed to be chronological).
        laps: All `LapMessage` instances from the file, in original order.
        profile: A `Profile` object. Only the anthropometric fields
            (`weight_kg`, `age`, `sex`) are consulted, and only when the
            HR-based fallback is used.

    Returns:
        A `CalorieResult` with `method="none"` if there isn't enough data
        to estimate; otherwise the session total and a per-lap split.
    """
    timed = [r for r in records if r.timestamp is not None]
    if len(timed) < 2:
        return CalorieResult(0, [], "none", "fewer than 2 timestamped records")

    method = _choose_method(timed, profile)
    if method == "none":
        return CalorieResult(
            0,
            [],
            "none",
            "no power data and HR fallback inputs (weight/age/sex) missing",
        )

    per_sample_kcal, hr_filled = _per_sample_kcal(timed, method, profile)
    total = int(round(sum(per_sample_kcal)))

    per_lap = _split_by_lap(timed, per_sample_kcal, laps, total) if laps else []

    reason = f"computed from {len(timed)} samples using {method}"
    if hr_filled:
        reason += f", {hr_filled} samples filled from HR"

    return CalorieResult(
        total_calories=total,
        per_lap_calories=per_lap,
        method=method,
        reason=reason,
    )


def _choose_method(records: Sequence[RecordMessage], profile) -> str:
    """Decide between power, hr, or none based on data and profile."""
    with_power = sum(1 for r in records if _valid_power(r.power))
    if with_power / len(records) >= _COVERAGE_THRESHOLD:
        return "power"

    if _has_hr_inputs(profile):
        with_hr = sum(1 for r in records if _valid_hr(r.heart_rate))
        if with_hr / len(records) >= _COVERAGE_THRESHOLD:
            return "hr"

    return "none"


def _per_sample_kcal(
    records: Sequence[RecordMessage], method: str, profile
) -> tuple[list[float], int]:
    """Compute calories attributed to each sample interval.

    The energy for record `i` covers the gap `[record[i-1], record[i]]`. The
    first record produces zero energy because there is no preceding interval.

    The power method integrates trapezoidally (mean of the two endpoint
    readings) when both endpoints are valid; a single valid endpoint is used
    as-is, which smooths over brief sensor dropouts. When neither endpoint
    has power (e.g., the meter died mid-ride), the interval is estimated from
    heart rate via the Keytel formula, provided the profile carries the
    required weight/age/sex — otherwise it contributes zero.

    Returns:
        Tuple of (per-sample kcal list, number of power-method intervals
        that were filled from heart rate).
    """
    out: list[float] = [0.0]
    hr_filled = 0
    can_fall_back_to_hr = _has_hr_inputs(profile)
    for i in range(1, len(records)):
        prev = records[i - 1]
        cur = records[i]
        dt = max(0.0, min(_MAX_SAMPLE_GAP_S, (cur.timestamp - prev.timestamp) / 1000.0))
        if dt == 0.0:
            out.append(0.0)
            continue

        if method == "power":
            prev_ok = _valid_power(prev.power)
            cur_ok = _valid_power(cur.power)
            if prev_ok and cur_ok:
                watts = (prev.power + cur.power) / 2.0
            elif prev_ok or cur_ok:
                watts = prev.power if prev_ok else cur.power
            elif can_fall_back_to_hr and _valid_hr(cur.heart_rate):
                # Power meter dropout: estimate this interval from HR instead
                # of counting zero work.
                hr_filled += 1
                out.append(_keytel_kcal_per_min(cur.heart_rate, profile) * dt / 60.0)
                continue
            else:
                out.append(0.0)
                continue
            # kJ of mechanical work → kcal of metabolic expenditure, using
            # GE = 22% (industry default; see _GROSS_EFFICIENCY above).
            out.append(watts * dt / 1000.0 * _KJ_TO_KCAL)
        else:  # hr
            if not _valid_hr(cur.heart_rate):
                out.append(0.0)
                continue
            out.append(_keytel_kcal_per_min(cur.heart_rate, profile) * dt / 60.0)

    return out, hr_filled


def _keytel_kcal_per_min(hr: int, profile) -> float:
    """Keytel et al. (2005) calorie expenditure regression.

    Returns kcal/minute for an instantaneous heart rate sample.
    """
    weight = profile.weight_kg
    age = profile.age
    if profile.sex == "male":
        # kJ/min → kcal/min via /4.184
        return max(
            0.0,
            (-55.0969 + 0.6309 * hr + 0.1988 * weight + 0.2017 * age) / 4.184,
        )
    # female
    return max(
        0.0,
        (-20.4022 + 0.4472 * hr - 0.1263 * weight + 0.074 * age) / 4.184,
    )


def _split_by_lap(
    records: Sequence[RecordMessage],
    per_sample_kcal: Sequence[float],
    laps: Sequence[LapMessage],
    total: int,
) -> list[int]:
    """Distribute the per-sample energy across the given laps.

    A sample is attributed to the first lap whose `[start_time, end_time]`
    range contains its timestamp. Records before any lap (which is rare but
    possible) are attributed to the first lap; records after the last lap
    end up in the last lap. The result is then renormalized so its sum
    matches the session total exactly (compensates for rounding).
    """
    ranges: list[tuple[int, int]] = []
    for lap in laps:
        start = lap.start_time
        end = lap.timestamp
        if start is None or end is None:
            # Fall back to elapsed-time math if endpoints missing.
            if start is None and end is not None and lap.total_elapsed_time is not None:
                start = int(end - lap.total_elapsed_time * 1000)
            elif (
                end is None and start is not None and lap.total_elapsed_time is not None
            ):
                end = int(start + lap.total_elapsed_time * 1000)
            else:
                ranges.append((0, 0))
                continue
        ranges.append((start, end))

    buckets = [0.0] * len(laps)
    for rec, kcal in zip(records, per_sample_kcal):
        if kcal == 0.0:
            continue
        ts = rec.timestamp
        idx = _lap_index_for_timestamp(ts, ranges)
        buckets[idx] += kcal

    rounded = [int(round(b)) for b in buckets]
    drift = total - sum(rounded)
    if rounded:
        rounded[-1] += drift
    return rounded


def _lap_index_for_timestamp(ts: int, ranges: Sequence[tuple[int, int]]) -> int:
    """Return the lap index this timestamp belongs to.

    Timestamps that fall between laps (e.g., a recording pause spanning a lap
    boundary) or before the first lap are attributed to the next lap to
    start; anything after the last lap goes to the last lap.
    """
    for i, (start, end) in enumerate(ranges):
        if start <= ts <= end:
            return i
    for i, (start, _end) in enumerate(ranges):
        if ts < start:
            return i
    return len(ranges) - 1
