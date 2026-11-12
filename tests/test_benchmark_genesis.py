"""Smoke tests for benchmark math and subprocess CLI contracts."""
from pathlib import Path
import math
import pytest

pytest.importorskip("psutil")
from tools.benchmark_genesis import commands, percentile, summary


def test_percentiles_are_interpolated():
    assert percentile([1, 2, 3], .95) == pytest.approx(2.9)
    assert percentile([3], .95) == 3


def test_summary_does_not_mix_sample_counts():
    observations = [
        {"metrics": {"wall_seconds": n, "observed_peak_rss_bytes": 100 * n},
         "dataset": {"total_parquet_bytes": 50 * n}}
        for n in (1, 2, 3)
    ]
    result = summary(observations)
    assert result["runs"] == 3
    assert result["wall_median_seconds"] == 2
    assert result["wall_p95_seconds"] == pytest.approx(2.9)
    assert result["sampled_peak_rss_max_bytes"] == 300
    assert result["parquet_bytes_median"] == 100


def test_commands_share_seed_and_student_count():
    destination = Path("data/test-out")
    for engine in ("python_v2_duckdb", "python_v3_pyarrow", "rust_pyarrow_bridge", "rust_native_parquet"):
        command = commands(
            output=destination, students=7, seed=20261029,
            catalog=Path("examples/atlas.demo.json"), engine=engine,
            batch_students=5, row_group_rows=64,
            rust_binary=Path("genesis-rs"),
        )
        assert "20261029" in command
        assert "7" in command
        assert str(destination) in command
        assert "examples/atlas.demo.json" in command


def test_unknown_engine_is_rejected():
    with pytest.raises(ValueError, match="unknown engine"):
        commands(output=Path("x"), students=3, seed=1,
                 catalog=Path("catalog.json"), engine="unknown",
                 batch_students=1, row_group_rows=2, rust_binary=Path("rust"))
