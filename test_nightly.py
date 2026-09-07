"""
Unit and Integration Test Suite for the Nightly Multi-Retailer Assessment Pipeline.
Verifies proxy rotation, AIMD adaptive rate limiting, circuit breaking, and SQLite checkpointing.
"""

import asyncio
import os
import tempfile
import time
from datetime import datetime, timezone

from models import CouponFinding, TriageStatus
from nightly import (
    AdaptiveTokenBucket,
    CheckpointStore,
    FingerprintRotator,
    NightlyPipeline,
    ProxyRotator,
    RetailerCircuitBreaker,
)


def test_proxy_rotator():
    proxies = ["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"]
    rotator = ProxyRotator(proxies, max_failures=2, cooldown_sec=10.0)

    loop = asyncio.new_event_loop()
    try:
        # 1. Round-robin rotation
        p1 = loop.run_until_complete(rotator.get_next_proxy())
        p2 = loop.run_until_complete(rotator.get_next_proxy())
        p3 = loop.run_until_complete(rotator.get_next_proxy())
        assert {p1, p2, p3} == set(proxies), "Proxies should rotate in round-robin"

        # 2. Record failure threshold
        loop.run_until_complete(rotator.record_result(p1, success=False))
        loop.run_until_complete(rotator.record_result(p1, success=False))

        # Node p1 should now be cooling down; next requests should avoid p1
        next_p = loop.run_until_complete(rotator.get_next_proxy())
        assert next_p != p1, f"Cooling proxy {p1} should not be selected while others are healthy"

        # 3. Success resets failure count
        loop.run_until_complete(rotator.record_result(p2, success=True, latency_ms=45.0))
        node_p2 = next(n for n in rotator.proxies if n.url == p2)
        assert node_p2.consecutive_success >= 1
        assert node_p2.failure_count == 0
        print("[PASS] ProxyRotator tests passed.")
    finally:
        loop.close()


def test_fingerprint_rotator():
    impersonate, headers = FingerprintRotator.get_random_profile()
    assert impersonate in ["chrome124", "chrome120", "edge101", "safari17_0"]
    assert "User-Agent" in headers
    assert "Accept-Language" in headers
    print("[PASS] FingerprintRotator tests passed.")


def test_adaptive_token_bucket():
    loop = asyncio.new_event_loop()
    try:
        limiter = AdaptiveTokenBucket(target_rps=10.0, min_rps=2.0, max_rps=20.0)
        assert limiter.current_rps == 10.0

        # Test Multiplicative Decrease on 429
        loop.run_until_complete(limiter.on_feedback(429, TriageStatus.RATE_LIMITED))
        assert limiter.current_rps == 5.0, f"Expected 5.0 rps, got {limiter.current_rps}"

        loop.run_until_complete(limiter.on_feedback(429, TriageStatus.RATE_LIMITED))
        assert limiter.current_rps == 2.5, f"Expected 2.5 rps, got {limiter.current_rps}"

        loop.run_until_complete(limiter.on_feedback(429, TriageStatus.RATE_LIMITED))
        assert limiter.current_rps == 2.0, "Should clamp at min_rps=2.0"

        # Test Additive Increase on 200 OK
        loop.run_until_complete(limiter.on_feedback(200, TriageStatus.INVALID))
        assert round(limiter.current_rps, 1) == 2.1, f"Expected 2.1 rps, got {limiter.current_rps}"
        print("[PASS] AdaptiveTokenBucket AIMD tests passed.")
    finally:
        loop.close()


def test_retailer_circuit_breaker():
    cb = RetailerCircuitBreaker(retailer_name="test_retailer", failure_threshold=3, recovery_timeout_sec=0.2)
    assert cb.can_proceed() is True
    assert cb.state == "CLOSED"

    # Record non-tripping failures
    tripped = cb.record_failure("timeout 1")
    assert tripped is False
    assert cb.can_proceed() is True

    tripped = cb.record_failure("timeout 2")
    assert tripped is False
    assert cb.can_proceed() is True

    # 3rd failure trips the breaker
    tripped = cb.record_failure("timeout 3")
    assert tripped is True
    assert cb.state == "OPEN"
    assert cb.can_proceed() is False

    # Wait for recovery timeout
    time.sleep(0.25)
    assert cb.can_proceed() is True
    assert cb.state == "HALF_OPEN"

    # Success closes it
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.consecutive_failures == 0
    print("[PASS] RetailerCircuitBreaker tests passed.")


def test_checkpoint_store():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_file = os.path.join(tmpdir, "test_checkpoint.db")
        store = CheckpointStore(db_path=db_file)

        # Initially empty
        probed = store.get_probed_codes("talron")
        assert len(probed) == 0

        # Record findings
        f1 = CouponFinding(
            code="save10",
            is_valid=True,
            status=TriageStatus.APPLIED,
            message="10% discount applied",
            http_status=200,
            response_time_ms=120.5,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        f2 = CouponFinding(
            code="invalid99",
            is_valid=False,
            status=TriageStatus.INVALID,
            message="Coupon does not exist",
            http_status=200,
            response_time_ms=85.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        store.record_finding("talron", f1)
        store.record_finding("talron", f2)

        # Verify retrieval
        probed = store.get_probed_codes("talron")
        assert probed == {"save10", "invalid99"}

        valid = store.get_valid_findings("talron")
        assert len(valid) == 1
        assert valid[0].code == "save10"
        assert valid[0].is_valid is True

        # Verify retailer isolation
        orlando_probed = store.get_probed_codes("orlando")
        assert len(orlando_probed) == 0

        print("[PASS] CheckpointStore tests passed.")


def test_canonical_retailers():
    canonical = NightlyPipeline.get_canonical_retailers()
    assert set(canonical) == {"talron", "orlando", "ringer", "spring", "bobot"}
    print(f"[PASS] Canonical retailers resolved: {canonical}")


if __name__ == "__main__":
    test_proxy_rotator()
    test_fingerprint_rotator()
    test_adaptive_token_bucket()
    test_retailer_circuit_breaker()
    test_checkpoint_store()
    test_canonical_retailers()
    print("\nAll Nightly Pipeline Unit Tests Passed Successfully!")
