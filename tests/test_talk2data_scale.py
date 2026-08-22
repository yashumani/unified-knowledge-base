from ukb.talk2data.scale import PROFILES, run_scale_benchmark


def test_unit_scale_profile_has_no_cross_tenant_leakage() -> None:
    result = run_scale_benchmark(PROFILES["unit"])

    assert result.passed is True
    assert result.episodes_created == 10
    assert result.memories_created == 100
    assert result.cross_tenant_leakage_count == 0
    assert result.coverage_status in {"complete", "partial"}
    assert result.query_p95_ms < 1500
