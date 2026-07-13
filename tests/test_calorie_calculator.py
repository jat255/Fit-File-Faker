"""Tests for fit_file_faker.calorie_calculator.

The calculator only reads `timestamp`, `power`, and `heart_rate` off the
record objects and `start_time`/`timestamp` off lap objects. We use lightweight
namespace stand-ins instead of constructing real fit_tool messages.
"""

from types import SimpleNamespace

from fit_file_faker.calorie_calculator import (
    CalorieResult,
    _MAX_SAMPLE_GAP_S,
    calculate_from_records,
)


def _rec(ts_ms, power=None, hr=None):
    return SimpleNamespace(timestamp=ts_ms, power=power, heart_rate=hr)


def _lap(start_ms, end_ms, elapsed=None):
    return SimpleNamespace(
        start_time=start_ms, timestamp=end_ms, total_elapsed_time=elapsed
    )


def _profile(weight_kg=None, age=None, sex=None):
    return SimpleNamespace(
        weight_kg=weight_kg,
        age=age,
        sex=sex,
        recalculate_calories=True,
    )


class TestCalculateFromRecords:
    def test_power_based_total_matches_kJ(self):
        # 100 W sustained for 600 s = 60,000 J = 60 kJ.
        # Metabolic conversion at GE = 22%: 60 / (0.22 * 4.184) ≈ 65 kcal.
        records = [_rec(i * 1000, power=100) for i in range(601)]
        result = calculate_from_records(records, laps=[], profile=_profile())
        assert result.method == "power"
        assert abs(result.total_calories - 65) <= 1

    def test_zero_power_yields_zero_calories(self):
        records = [_rec(i * 1000, power=0) for i in range(120)]
        result = calculate_from_records(records, laps=[], profile=_profile())
        assert result.method == "power"
        assert result.total_calories == 0

    def test_hr_fallback_when_power_missing(self):
        # No power, but HR present and profile has anthropometrics.
        # Male, 70 kg, 30 yr, HR 150 → roughly 13 kcal/min by Keytel.
        records = [_rec(i * 1000, hr=150) for i in range(601)]
        result = calculate_from_records(
            records,
            laps=[],
            profile=_profile(weight_kg=70.0, age=30, sex="male"),
        )
        assert result.method == "hr"
        # Keytel @ HR 150, 70 kg, 30 yr, male ≈ 14.2 kcal/min × 10 min ≈ 142 kcal
        assert 135 <= result.total_calories <= 150

    def test_returns_none_when_no_power_and_no_hr_inputs(self):
        records = [_rec(i * 1000, hr=150) for i in range(30)]
        # profile has neither weight nor age nor sex
        result = calculate_from_records(records, laps=[], profile=_profile())
        assert result.method == "none"
        assert result.total_calories == 0

    def test_returns_none_when_too_few_records(self):
        result = calculate_from_records(
            [_rec(0, power=200)], laps=[], profile=_profile()
        )
        assert result.method == "none"

    def test_per_lap_split_sums_to_session_total(self):
        # Two 5-minute laps at 100 W each → total ~60 kcal.
        records = [_rec(i * 1000, power=100) for i in range(601)]
        laps = [
            _lap(0, 300_000),
            _lap(300_000, 600_000),
        ]
        result = calculate_from_records(records, laps=laps, profile=_profile())
        assert len(result.per_lap_calories) == 2
        assert sum(result.per_lap_calories) == result.total_calories

    def test_gap_in_recording_is_capped(self):
        # Two samples 10 minutes apart shouldn't count as a 10-minute interval.
        records = [_rec(0, power=200), _rec(600_000, power=200)]
        result = calculate_from_records(records, laps=[], profile=_profile())
        # Gap is clamped to _MAX_SAMPLE_GAP_S → 200 W * 30 s = 6 kJ.
        # At GE = 22%: 6 / (0.22 * 4.184) ≈ 6.5 → 7 kcal.
        kj = 200 * _MAX_SAMPLE_GAP_S / 1000
        expected = round(kj / (0.22 * 4.184))
        assert result.total_calories == expected

    def test_trapezoidal_integration_between_sparse_samples(self):
        # 0 W → 200 W over a 20 s gap. Trapezoidal mean is 100 W → 2 kJ
        # → ~2.2 kcal. Right-rectangle integration would take 200 W → 4 kJ
        # → ~4.3 kcal, so the rounded totals differ.
        records = [_rec(0, power=0), _rec(20_000, power=200)]
        result = calculate_from_records(records, laps=[], profile=_profile())
        assert result.method == "power"
        assert result.total_calories == 2

    def test_single_sample_dropout_uses_valid_endpoint(self):
        # Middle sample lost power (brief ANT+ dropout): both surrounding
        # intervals still integrate using their one valid endpoint (200 W),
        # so 2 × 200 W × 10 s = 4 kJ → ~4.3 → 4 kcal.
        records = [
            _rec(0, power=200),
            _rec(10_000, power=None),
            _rec(20_000, power=200),
        ]
        result = calculate_from_records(records, laps=[], profile=_profile())
        assert result.method == "power"
        assert result.total_calories == 4
        assert "filled from HR" not in result.reason

    def test_power_dropout_falls_back_to_hr_per_sample(self):
        # Power meter dies halfway: first 5 min at 200 W (~65 kcal), second
        # 5 min power-less but with HR 150 and a complete profile
        # (~14 kcal/min by Keytel → ~70 kcal). Both halves must count.
        records = [_rec(i * 1000, power=200) for i in range(301)]
        records += [_rec(i * 1000, hr=150) for i in range(301, 601)]
        result = calculate_from_records(
            records,
            laps=[],
            profile=_profile(weight_kg=70.0, age=30, sex="male"),
        )
        assert result.method == "power"
        assert "filled from HR" in result.reason
        assert 125 <= result.total_calories <= 150

    def test_power_dropout_without_hr_inputs_counts_zero(self):
        # Same dropout but no anthropometrics in the profile: the power-less
        # half contributes nothing, leaving just the first half (~65 kcal).
        records = [_rec(i * 1000, power=200) for i in range(301)]
        records += [_rec(i * 1000, hr=150) for i in range(301, 601)]
        result = calculate_from_records(records, laps=[], profile=_profile())
        assert result.method == "power"
        assert "filled from HR" not in result.reason
        assert 60 <= result.total_calories <= 70

    def test_sample_between_laps_goes_to_next_lap(self):
        # Three equal-effort thirds, but the lap ranges leave a 20 s hole
        # between lap 1 and lap 2. Samples in the hole must land in lap 2
        # (the next lap to start), not in the last lap.
        records = [_rec(i * 1000, power=100) for i in range(601)]
        laps = [
            _lap(0, 200_000),
            _lap(220_000, 400_000),
            _lap(400_000, 600_000),
        ]
        result = calculate_from_records(records, laps=laps, profile=_profile())
        assert sum(result.per_lap_calories) == result.total_calories
        # With the hole attributed to lap 2, all three laps cover ~200 s of
        # equal effort; the old "dump into last lap" behaviour would make
        # lap 3 ~20 s heavier than lap 2.
        lap_kcals = result.per_lap_calories
        assert max(lap_kcals) - min(lap_kcals) <= 2

    def test_sample_before_first_lap_goes_to_first_lap(self):
        # 10 s of riding before the first lap starts must count towards it.
        records = [_rec(i * 1000, power=100) for i in range(601)]
        laps = [
            _lap(10_000, 300_000),
            _lap(300_000, 600_000),
        ]
        result = calculate_from_records(records, laps=laps, profile=_profile())
        assert sum(result.per_lap_calories) == result.total_calories
        assert result.per_lap_calories[0] >= result.per_lap_calories[1]


class TestCalorieResultDataclass:
    def test_default_field_types(self):
        r = CalorieResult(
            total_calories=42,
            per_lap_calories=[10, 20, 12],
            method="power",
            reason="ok",
        )
        assert r.total_calories == 42
        assert r.per_lap_calories == [10, 20, 12]
        assert r.method == "power"
