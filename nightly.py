"""
Nightly Scheduled Multi-Retailer Assessment Pipeline
Production-ready, fault-tolerant orchestration engine for multi-hour security assessment runs.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import logging
import os
import random
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Fix Windows console UTF-8 output for Hebrew characters
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import CurlError, RequestsError

from models import CouponFinding, TriageStatus
from strategies import BaseRetailerStrategy, RETAILER_REGISTRY, get_retailer_strategy
from wordlist import WordlistEngine

# ==============================================================================
# 1. Structured Logging & Telemetry Setup
# ==============================================================================

def setup_nightly_logger(log_dir: str = "logs") -> logging.Logger:
    """Configures structured, rotational logging for multi-hour operations."""
    os.makedirs(log_dir, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"nightly_{date_str}.log")

    logger = logging.getLogger("nightly_pipeline")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File Handler (Detailed DEBUG logs with JSON formatting)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": %(message)s}'
    )
    fh.setFormatter(file_formatter)
    logger.addHandler(fh)

    # Console Handler (Clean, high-level INFO logs)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)

    return logger

logger = setup_nightly_logger()

# ==============================================================================
# 2. Proxy Rotator with Health & Cooldown Tracking
# ==============================================================================

@dataclass
class ProxyNode:
    url: str
    failure_count: int = 0
    consecutive_success: int = 0
    cooldown_until: float = 0.0
    latency_sum_ms: float = 0.0
    total_requests: int = 0

class ProxyRotator:
    """Thread-safe proxy pool with exponential cooldown and health penalization."""

    def __init__(self, proxy_list: Optional[List[str]] = None, max_failures: int = 3, cooldown_sec: float = 60.0):
        self.proxies: List[ProxyNode] = [ProxyNode(url=p.strip()) for p in (proxy_list or []) if p.strip()]
        self.max_failures = max_failures
        self.cooldown_sec = cooldown_sec
        self._lock = asyncio.Lock()
        self._cursor = 0

    @property
    def has_proxies(self) -> bool:
        return len(self.proxies) > 0

    async def get_next_proxy(self) -> Optional[str]:
        """Returns the next healthy proxy using round-robin, skipping cooling proxies."""
        if not self.proxies:
            return None

        async with self._lock:
            now = time.monotonic()
            for _ in range(len(self.proxies)):
                node = self.proxies[self._cursor]
                self._cursor = (self._cursor + 1) % len(self.proxies)
                if node.cooldown_until <= now:
                    return node.url

            # All proxies cooling down; return the one cooling fastest
            return min(self.proxies, key=lambda n: n.cooldown_until).url

    async def record_result(self, proxy_url: Optional[str], success: bool, latency_ms: float = 0.0):
        """Updates health statistics for the proxy."""
        if not proxy_url:
            return
        async with self._lock:
            for node in self.proxies:
                if node.url == proxy_url:
                    node.total_requests += 1
                    if success:
                        node.consecutive_success += 1
                        node.failure_count = max(0, node.failure_count - 1)
                        node.latency_sum_ms += latency_ms
                    else:
                        node.consecutive_success = 0
                        node.failure_count += 1
                        if node.failure_count >= self.max_failures:
                            penalty = self.cooldown_sec * (2 ** (node.failure_count - self.max_failures))
                            node.cooldown_until = time.monotonic() + penalty
                            logger.warning(
                                json.dumps({
                                    "event": "proxy_penalized",
                                    "proxy": node.url,
                                    "failures": node.failure_count,
                                    "cooldown_sec": round(penalty, 1),
                                })
                            )
                    break

# ==============================================================================
# 3. Fingerprint & User-Agent Rotator
# ==============================================================================

class FingerprintRotator:
    """Rotates TLS impersonation profiles and cohesive client hints."""

    PROFILES = [
        ("chrome124", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
        ("chrome120", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        ("edge101", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.53"),
        ("safari17_0", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
    ]

    @classmethod
    def get_random_profile(cls) -> Tuple[str, Dict[str, str]]:
        impersonate, ua = random.choice(cls.PROFILES)
        headers = {
            "User-Agent": ua,
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        return impersonate, headers

# ==============================================================================
# 4. Adaptive Token-Bucket Rate Limiter (AIMD Congestion Control)
# ==============================================================================

class AdaptiveTokenBucket:
    """
    Per-domain token-bucket rate limiter implementing Additive Increase /
    Multiplicative Decrease (AIMD) for automatic self-throttling on HTTP 429.
    """

    def __init__(self, target_rps: float = 6.0, min_rps: float = 1.0, max_rps: float = 15.0):
        self.current_rps = target_rps
        self.min_rps = min_rps
        self.max_rps = max_rps
        self.capacity = max_rps
        self.tokens = self.current_rps
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquires a transmission token, sleeping if rate limit is exhausted."""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.current_rps)

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                sleep_time = (1.0 - self.tokens) / self.current_rps
            await asyncio.sleep(sleep_time)

    async def on_feedback(self, status_code: int, status: str):
        """Adjusts rate limit dynamically based on server response."""
        async with self._lock:
            if status_code == 429 or status == TriageStatus.RATE_LIMITED:
                # Multiplicative Decrease: Throttle by 50% immediately
                self.current_rps = max(self.min_rps, self.current_rps * 0.5)
                logger.warning(
                    json.dumps({
                        "event": "aimd_throttle",
                        "reason": "rate_limited",
                        "new_rps": round(self.current_rps, 1),
                    })
                )
            elif status_code == 200 and status not in (TriageStatus.EXPIRED_NONCE, TriageStatus.WAF_CHALLENGE):
                # Additive Increase: Slowly ramp up (+0.1 req/s)
                self.current_rps = min(self.max_rps, self.current_rps + 0.1)

# ==============================================================================
# 5. Circuit Breaker for Retailer Fault Isolation
# ==============================================================================

class RetailerCircuitBreaker:
    """Per-retailer circuit breaker ensuring single-target failures don't crash nightly run."""

    def __init__(self, retailer_name: str, failure_threshold: int = 15, recovery_timeout_sec: float = 300.0):
        self.retailer_name = retailer_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_sec
        self.consecutive_failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.tripped_at: float = 0.0

    def record_success(self):
        self.consecutive_failures = 0
        self.state = "CLOSED"

    def record_failure(self, reason: str) -> bool:
        """Records a failure; returns True if circuit is tripped OPEN."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold and self.state != "OPEN":
            self.state = "OPEN"
            self.tripped_at = time.monotonic()
            logger.error(
                json.dumps({
                    "event": "circuit_breaker_tripped",
                    "retailer": self.retailer_name,
                    "reason": reason,
                    "consecutive_failures": self.consecutive_failures,
                })
            )
            return True
        return False

    def can_proceed(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.monotonic() - self.tripped_at > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"[CIRCUIT BREAKER] Half-open probe window active for '{self.retailer_name}'")
                return True
            return False
        return True

# ==============================================================================
# 6. Atomic State Checkpointing Store (SQLite WAL Mode)
# ==============================================================================

class CheckpointStore:
    """Atomic, SQLite-backed progress checkpoint store supporting clean resumption."""

    def __init__(self, db_path: str = "nightly_checkpoint.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS probed_coupons (
                    retailer TEXT NOT NULL,
                    code TEXT NOT NULL,
                    is_valid INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    http_status INTEGER NOT NULL,
                    response_time_ms REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (retailer, code)
                );
            """)
            conn.commit()

    def get_probed_codes(self, retailer: str) -> Set[str]:
        """Retrieves set of already tested codes for a retailer."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM probed_coupons WHERE retailer = ?", (retailer,))
            return {row[0] for row in cursor.fetchall()}

    def get_valid_findings(self, retailer: str) -> List[CouponFinding]:
        """Retrieves all valid discoveries recorded for a retailer."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT code, is_valid, status, message, http_status, response_time_ms, timestamp
                FROM probed_coupons 
                WHERE retailer = ? AND is_valid = 1
                """,
                (retailer,),
            )
            return [
                CouponFinding(
                    code=row[0],
                    is_valid=bool(row[1]),
                    status=row[2],
                    message=row[3],
                    http_status=row[4],
                    response_time_ms=row[5],
                    timestamp=row[6],
                )
                for row in cursor.fetchall()
            ]

    def record_finding(self, retailer: str, finding: CouponFinding):
        """Records a single probe result atomically."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO probed_coupons 
                (retailer, code, is_valid, status, message, http_status, response_time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    retailer,
                    finding.code,
                    1 if finding.is_valid else 0,
                    finding.status,
                    finding.message,
                    finding.http_status,
                    finding.response_time_ms,
                    finding.timestamp,
                ),
            )
            conn.commit()

# ==============================================================================
# 7. Metrics Aggregator & Audit Reporter
# ==============================================================================

@dataclass
class RetailerMetrics:
    name: str
    total_candidates: int = 0
    tested: int = 0
    valid_hits: int = 0
    rate_limited_429: int = 0
    network_errors: int = 0
    circuit_breaker_tripped: bool = False
    start_time: float = 0.0
    end_time: float = 0.0
    findings: List[CouponFinding] = field(default_factory=list)

class MetricsAggregator:
    """Aggregates execution metrics across all retailers and formats reports."""

    def __init__(self):
        self.start_time = time.monotonic()
        self.retailers: Dict[str, RetailerMetrics] = {}

    def init_retailer(self, name: str, total_candidates: int) -> RetailerMetrics:
        rm = RetailerMetrics(name=name, total_candidates=total_candidates, start_time=time.monotonic())
        self.retailers[name] = rm
        return rm

    def generate_report(self, output_dir: str = "reports") -> Tuple[str, str]:
        """Saves structured JSON and Markdown executive audit reports."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        elapsed_total = time.monotonic() - self.start_time

        summary = {
            "execution_date": datetime.now(timezone.utc).isoformat(),
            "total_runtime_seconds": round(elapsed_total, 2),
            "total_retailers": len(self.retailers),
            "retailers": {},
        }

        md_lines = [
            "# Nightly Coupon Assessment Executive Audit Report",
            f"**Execution Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Total Runtime:** {elapsed_total / 3600:.2f} hours ({elapsed_total:.1f}s)",
            "",
            "## Retailer Execution Summary",
            "| Retailer | Tested / Total | Valid Hits | 429 Throttled | Network Errors | Circuit Status |",
            "|---|---|---|---|---|---|",
        ]

        for name, rm in self.retailers.items():
            status = "TRIPPED" if rm.circuit_breaker_tripped else "COMPLETED"
            summary["retailers"][name] = {
                "tested": rm.tested,
                "total": rm.total_candidates,
                "valid_hits": rm.valid_hits,
                "rate_limited_429": rm.rate_limited_429,
                "network_errors": rm.network_errors,
                "status": status,
                "findings": [
                    {
                        "code": f.code,
                        "status": f.status,
                        "message": f.message,
                        "http_status": f.http_status,
                        "response_time_ms": f.response_time_ms,
                        "timestamp": f.timestamp,
                    }
                    for f in rm.findings
                ],
            }
            md_lines.append(
                f"| `{name}` | {rm.tested} / {rm.total_candidates} | **{rm.valid_hits}** | "
                f"{rm.rate_limited_429} | {rm.network_errors} | `{status}` |"
            )

        md_lines.append("\n## Valid / Active Promotional Findings")
        has_any_finding = False
        for name, rm in self.retailers.items():
            if rm.findings:
                has_any_finding = True
                md_lines.append(f"\n### Retailer: `{name}`")
                for f in rm.findings:
                    md_lines.append(f"- **`{f.code}`** (`{f.status}`) — HTTP {f.http_status} ({f.response_time_ms}ms)")
                    md_lines.append(f"  *Server Notice:* {f.message}")

        if not has_any_finding:
            md_lines.append("\n*No valid or active promotional codes discovered during this run.*")

        # Save report files
        json_path = os.path.join(output_dir, f"nightly_report_{timestamp}.json")
        md_path = os.path.join(output_dir, f"nightly_report_{timestamp}.md")

        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(summary, jf, indent=2, ensure_ascii=False)

        with open(md_path, "w", encoding="utf-8") as mf:
            mf.write("\n".join(md_lines) + "\n")

        logger.info(f"[+] Nightly reports generated successfully:\n    - {md_path}\n    - {json_path}")
        return md_path, json_path

# ==============================================================================
# 8. Core Nightly Orchestrator
# ==============================================================================

class NightlyPipeline:
    """
    Main pipeline orchestrator managing multi-retailer scheduling, resilient
    workers, proxy rotation, jitter backoff, checkpointing, and reporting.
    """

    def __init__(
        self,
        retailer_names: Optional[List[str]] = None,
        concurrency_per_retailer: int = 5,
        target_rps_per_retailer: float = 6.0,
        proxy_file: Optional[str] = None,
        resume: bool = True,
        max_retries: int = 4,
        jitter_ms: Tuple[int, int] = (100, 400),
        limit: Optional[int] = None,
        include_leetspeak: bool = True,
        db_path: str = "nightly_checkpoint.db",
    ):
        self.retailer_names = self._resolve_retailers(retailer_names)
        self.concurrency_per_retailer = concurrency_per_retailer
        self.target_rps = target_rps_per_retailer
        self.resume = resume
        self.max_retries = max_retries
        self.jitter_ms = jitter_ms
        self.limit = limit
        self.include_leetspeak = include_leetspeak
        self.checkpoint = CheckpointStore(db_path=db_path)
        self.metrics = MetricsAggregator()
        self.stop_requested = False

        # Load proxies
        proxies = []
        if proxy_file and Path(proxy_file).is_file():
            with open(proxy_file, "r", encoding="utf-8") as f:
                proxies = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        self.proxy_rotator = ProxyRotator(proxies)

    @classmethod
    def get_canonical_retailers(cls) -> List[str]:
        """Returns the deduplicated list of canonical retailer names."""
        canonical = []
        seen_classes = set()
        for key, strat_cls in RETAILER_REGISTRY.items():
            if strat_cls not in seen_classes:
                seen_classes.add(strat_cls)
                canonical.append(key)
        return canonical

    def _resolve_retailers(self, names: Optional[List[str]]) -> List[str]:
        """Resolves unique canonical retailer strategies, filtering aliases."""
        canonical_list = self.get_canonical_retailers()
        if not names or "all" in [n.lower() for n in names]:
            return canonical_list

        resolved = []
        for n in names:
            key = n.strip().lower()
            if key in RETAILER_REGISTRY:
                strat = get_retailer_strategy(key)
                if strat.name not in resolved:
                    resolved.append(strat.name)
            else:
                logger.warning(f"Unknown retailer '{n}' ignored. Available: {', '.join(canonical_list)}")
        return resolved or canonical_list

    async def _probe_with_retry(
        self,
        strategy: BaseRetailerStrategy,
        limiter: AdaptiveTokenBucket,
        cb: RetailerCircuitBreaker,
        coupon: str,
        session_nonce: str,
    ) -> Optional[CouponFinding]:
        """Probes a single coupon with Full Jitter exponential backoff and proxy failover."""
        if not cb.can_proceed() or self.stop_requested:
            return None

        # Apply random micro-jitter
        jitter_s = random.uniform(self.jitter_ms[0], self.jitter_ms[1]) / 1000.0
        await asyncio.sleep(jitter_s)

        for attempt in range(1, self.max_retries + 1):
            if self.stop_requested:
                return None

            await limiter.acquire()

            # Rotate proxy and TLS profile per attempt
            proxy_url = await self.proxy_rotator.get_next_proxy()
            impersonate_profile, extra_headers = FingerprintRotator.get_random_profile()
            headers = {**strategy.headers, **extra_headers}
            payload = strategy.build_payload(coupon, session_nonce)

            t0 = time.perf_counter()
            try:
                async with AsyncSession(
                    headers=headers,
                    cookies=strategy.default_cookies,
                    impersonate=impersonate_profile,
                    proxy=proxy_url,
                    timeout=12.0,
                ) as client:
                    resp = await client.post(strategy.target_url, data=payload)
                    latency_ms = (time.perf_counter() - t0) * 1000.0

                    # Health & Rate Limiter updates
                    await self.proxy_rotator.record_result(proxy_url, success=True, latency_ms=latency_ms)
                    is_valid, status, msg = strategy.triage_response(resp.text, resp.status_code)
                    await limiter.on_feedback(resp.status_code, status)

                    if status in (TriageStatus.EXPIRED_NONCE, TriageStatus.WAF_CHALLENGE):
                        cb.record_failure(f"Auth/WAF rejection: {status}")
                    else:
                        cb.record_success()

                    return CouponFinding(
                        code=coupon,
                        is_valid=is_valid,
                        status=status,
                        message=msg,
                        http_status=resp.status_code,
                        response_time_ms=round(latency_ms, 2),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )

            except (RequestsError, CurlError, Exception) as exc:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                await self.proxy_rotator.record_result(proxy_url, success=False)

                if attempt < self.max_retries and not self.stop_requested:
                    # SRE Standard Full Jitter Backoff
                    backoff = random.uniform(0, min(8.0, 0.8 * (2 ** attempt)))
                    logger.debug(f"[Retry] Code '{coupon}' attempt {attempt} failed ({exc}). Backing off {backoff:.2f}s")
                    await asyncio.sleep(backoff)
                else:
                    cb.record_failure(f"Exhausted {self.max_retries} attempts: {exc}")
                    return CouponFinding(
                        code=coupon,
                        is_valid=False,
                        status=TriageStatus.NETWORK_ERROR,
                        message=f"Network error after {self.max_retries} attempts: {exc}",
                        http_status=0,
                        response_time_ms=round(latency_ms, 2),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )

    async def _process_retailer(self, retailer_name: str):
        """Worker task processing all permutations for a single retailer."""
        strategy = get_retailer_strategy(retailer_name)
        logger.info(f"[*] Starting Pipeline Worker for: {strategy.display_name} ({strategy.name})")

        # 1. Synthesize permutations
        all_candidates = WordlistEngine.generate_candidates(
            strategy=strategy,
            include_leetspeak=self.include_leetspeak,
        )
        if self.limit and self.limit > 0:
            all_candidates = all_candidates[: self.limit]

        rm = self.metrics.init_retailer(retailer_name, total_candidates=len(all_candidates))

        # 2. Checkpoint filtering (Resumability)
        already_probed = self.checkpoint.get_probed_codes(retailer_name) if self.resume else set()
        cached_valid = self.checkpoint.get_valid_findings(retailer_name) if self.resume else []
        rm.findings.extend(cached_valid)
        rm.valid_hits = len(cached_valid)

        queue = [c for c in all_candidates if c not in already_probed]
        rm.tested = len(all_candidates) - len(queue)

        logger.info(
            f"[{retailer_name}] Total Permutations: {len(all_candidates)} | "
            f"Cached: {rm.tested} | Remaining to Test: {len(queue)}"
        )

        if not queue:
            logger.info(f"[{retailer_name}] All permutations already tested in previous checkpoint. Skipping.")
            return

        limiter = AdaptiveTokenBucket(target_rps=self.target_rps)
        cb = RetailerCircuitBreaker(retailer_name=retailer_name, failure_threshold=15)
        semaphore = asyncio.Semaphore(self.concurrency_per_retailer)

        async def worker(code: str):
            async with semaphore:
                if not cb.can_proceed() or self.stop_requested:
                    return
                finding = await self._probe_with_retry(
                    strategy=strategy,
                    limiter=limiter,
                    cb=cb,
                    coupon=code,
                    session_nonce=strategy.default_nonce,
                )
                if finding:
                    self.checkpoint.record_finding(retailer_name, finding)
                    rm.tested += 1
                    if finding.is_valid:
                        rm.valid_hits += 1
                        rm.findings.append(finding)
                        logger.info(
                            f"    \033[92m[HIT: {retailer_name}]\033[0m Code: \033[1m{finding.code}\033[0m "
                            f"({finding.status}) -> {finding.message}"
                        )
                    elif finding.status == TriageStatus.RATE_LIMITED:
                        rm.rate_limited_429 += 1
                    elif finding.status == TriageStatus.NETWORK_ERROR:
                        rm.network_errors += 1

        # Bounded batch execution to prevent memory accumulation
        batch_size = 50
        for i in range(0, len(queue), batch_size):
            if self.stop_requested:
                logger.warning(f"[{retailer_name}] Interrupted by operator. Halting cleanly.")
                break

            if not cb.can_proceed():
                rm.circuit_breaker_tripped = True
                logger.error(f"[{retailer_name}] Circuit Breaker tripped. Halting execution for this retailer.")
                break

            batch = queue[i : i + batch_size]
            await asyncio.gather(*[worker(c) for c in batch])
            pct = (rm.tested / rm.total_candidates) * 100 if rm.total_candidates > 0 else 100.0
            logger.info(
                f"[{retailer_name}] Progress: {rm.tested}/{rm.total_candidates} ({pct:5.1f}%) | "
                f"Hits: {rm.valid_hits} | Errors: {rm.network_errors} | Speed: {limiter.current_rps:.1f} rps"
            )

        rm.end_time = time.monotonic()
        logger.info(f"[+] Finished Retailer: {retailer_name} (Hits: {rm.valid_hits}, 429s: {rm.rate_limited_429})")

    async def run(self):
        """Executes the complete nightly batch across all configured retailers."""
        start_wall_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print("\n" + "=" * 78, flush=True)
        print("          SENIOR APPEC NIGHTLY MULTI-RETAILER PIPELINE", flush=True)
        print("=" * 78, flush=True)
        logger.info(f"Execution Started     : {start_wall_time}")
        logger.info(f"Target Retailers      : {', '.join(self.retailer_names)}")
        logger.info(f"Worker Concurrency    : {self.concurrency_per_retailer} workers/target")
        logger.info(f"Domain Rate Limit     : {self.target_rps} req/s per target")
        logger.info(f"Checkpoint Database   : {self.checkpoint.db_path} (Resume: {self.resume})")
        logger.info(f"Proxy Pool Status     : {len(self.proxy_rotator.proxies)} active proxies\n")

        # Execute all retailers in parallel with per-domain isolation
        tasks = [self._process_retailer(r) for r in self.retailer_names]
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            self.stop_requested = True
            logger.warning("[!] Cancellation received. Finalizing reports...")

        # Generate audit report
        md_report, json_report = self.metrics.generate_report()
        print("\n" + "=" * 78, flush=True)
        print("              NIGHTLY PIPELINE EXECUTION SUMMARY", flush=True)
        print("=" * 78, flush=True)
        print(f"[+] Markdown Audit Report : {md_report}", flush=True)
        print(f"[+] JSON Telemetry Report : {json_report}", flush=True)
        print(f"[+] Checkpoint Database   : {self.checkpoint.db_path}", flush=True)


# ==============================================================================
# 9. Standalone CLI Entry Point
# ==============================================================================

def parse_nightly_arguments():
    available_retailers = NightlyPipeline.get_canonical_retailers() + ["all"]
    parser = argparse.ArgumentParser(
        description="Nightly Multi-Retailer Resilient Assessment Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--retailers",
        type=str,
        default="all",
        help=f"Target retailers (comma-separated or 'all'). Choices: {', '.join(available_retailers)}",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Worker concurrency per retailer (default: 5)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=6.0,
        help="Target requests per second per retailer (default: 6.0)",
    )
    parser.add_argument(
        "--proxies",
        type=str,
        default=None,
        help="Path to proxy list text file (one URL per line)",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume execution from checkpoint database (default: True)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max permutations to test per retailer (default: unlimited)",
    )
    parser.add_argument(
        "--leetspeak",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate leetspeak permutation variants (default: True)",
    )
    parser.add_argument(
        "--checkpoint-db",
        type=str,
        default="nightly_checkpoint.db",
        help="Path to SQLite checkpoint database (default: nightly_checkpoint.db)",
    )
    return parser.parse_args()


def main():
    args = parse_nightly_arguments()
    retailer_list = [r.strip() for r in args.retailers.split(",") if r.strip()]
    pipeline = NightlyPipeline(
        retailer_names=retailer_list,
        concurrency_per_retailer=args.concurrency,
        target_rps_per_retailer=args.rate_limit,
        proxy_file=args.proxies,
        resume=args.resume,
        limit=args.limit,
        include_leetspeak=args.leetspeak,
        db_path=args.checkpoint_db,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(pipeline.run())
    except KeyboardInterrupt:
        print("\n[!] Operator interrupted (SIGINT). Generating reports for progress so far...", flush=True)
        pipeline.stop_requested = True
        pipeline.metrics.generate_report()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
