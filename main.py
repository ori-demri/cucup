import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

# Fix Windows console UTF-8 output for Hebrew characters
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from models import CouponFinding, TriageStatus
from strategies import (
    BaseRetailerStrategy,
    OrlandoStrategy,
    TalronStrategy,
    RingerStrategy,
    SpringStrategy,
    BobotStrategy,
    RETAILER_REGISTRY,
    get_retailer_strategy,
)
from wordlist import WordlistEngine
from engine import Engine
from nightly import NightlyPipeline


def parse_cookie_string(raw_cookie: str) -> dict[str, str]:
    """Parses raw HTTP Cookie header string into a dictionary."""
    cookies = {}
    for item in raw_cookie.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def print_conclusion(
    strategy: BaseRetailerStrategy,
    findings: list[CouponFinding],
    stats: dict,
    stacking_result: dict,
    active_url: str,
    active_nonce: str,
):
    """Prints a structured security assessment conclusion directly to the console."""
    elapsed = stats.get("end_time", 0) - stats.get("start_time", 0)
    total_tested = stats.get("total_tested", 0)
    avg_rps = round(total_tested / elapsed, 2) if elapsed > 0 else 0
    valid_count = stats.get("valid_count", 0)
    rate_limited_count = stats.get("rate_limited_count", 0)
    errors_count = stats.get("errors_count", 0)

    print("\n" + "=" * 78, flush=True)
    print("                    SECURITY ASSESSMENT CONCLUSION", flush=True)
    print("=" * 78, flush=True)

    # 1. Executive Summary
    print("\n[+] Assessment Execution Summary:", flush=True)
    print(f"    - Target Retailer        : {strategy.display_name} ({strategy.name})", flush=True)
    print(f"    - Target Endpoint        : {active_url}", flush=True)
    print(f"    - Execution Time         : {elapsed:.2f}s", flush=True)
    print(f"    - Total Requests Sent    : {total_tested}", flush=True)
    print(f"    - Average Throughput     : {avg_rps} req/s", flush=True)
    print(f"    - Valid/Active Coupons   : {valid_count}", flush=True)
    print(f"    - Rate-Limited Hits (429): {rate_limited_count}", flush=True)
    if errors_count > 0:
        print(f"    - Network Errors         : {errors_count}", flush=True)

    # 2. Discovered Coupons
    print("\n[+] Discovered Promotional Codes:", flush=True)
    if findings:
        for idx, f in enumerate(findings, 1):
            status_color = "\033[92m" if f.is_valid else "\033[93m"
            poc_cmd = strategy.get_curl_poc(f.code, active_nonce)
            print(f"    {idx}. Code: \033[1m{f.code}\033[0m", flush=True)
            print(f"       Classification  : {status_color}{f.status}\033[0m (HTTP {f.http_status})", flush=True)
            print(f"       Latency         : {f.response_time_ms} ms", flush=True)
            print(f"       Server Notice   : {f.message}", flush=True)
            print(f"       PoC Verification: {poc_cmd}", flush=True)
    else:
        print("    [!] No valid or restricted promotional codes discovered.", flush=True)


def parse_arguments():
    available_retailers = list(RETAILER_REGISTRY.keys())
    canonical_retailers = NightlyPipeline.get_canonical_retailers()

    parser = argparse.ArgumentParser(
        description="Senior AppSec Multi-Retailer Coupon Enumeration & Business Logic Assessment Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Operational mode")

    # --- Nightly Pipeline Subcommand ('nightly') ---
    nightly_parser = subparsers.add_parser("nightly", help="Run multi-retailer resilient nightly pipeline")
    nightly_parser.add_argument(
        "--retailers",
        type=str,
        default="all",
        help=f"Target retailers (comma-separated or 'all'). Choices: {', '.join(canonical_retailers)}",
    )
    nightly_parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Worker concurrency per retailer (default: 5)",
    )
    nightly_parser.add_argument(
        "--rate-limit",
        type=float,
        default=6.0,
        help="Target req/s per retailer (default: 6.0)",
    )
    nightly_parser.add_argument(
        "--proxies",
        type=str,
        default=None,
        help="Path to proxy list text file",
    )
    nightly_parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume from checkpoint database (default: True)",
    )
    nightly_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max permutations to test per retailer (default: unlimited)",
    )
    nightly_parser.add_argument(
        "--leetspeak",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate leetspeak permutation variants (default: True)",
    )
    nightly_parser.add_argument(
        "--checkpoint-db",
        type=str,
        default="nightly_checkpoint.db",
        help="Path to checkpoint SQLite database (default: nightly_checkpoint.db)",
    )

    # --- Standalone single target options / root flags ---
    parser.add_argument(
        "--nightly",
        action="store_true",
        help="Run multi-retailer resilient nightly pipeline (flag alias for 'nightly' subcommand)",
    )
    parser.add_argument(
        "--retailers",
        type=str,
        default="all",
        help="For nightly mode: comma-separated retailers or 'all'",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=6.0,
        help="For nightly mode: target req/s per retailer (default: 6.0)",
    )
    parser.add_argument(
        "--proxies",
        type=str,
        default=None,
        help="For nightly mode: path to proxy list text file",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="For nightly mode: resume from checkpoint DB (default: True)",
    )
    parser.add_argument(
        "--checkpoint-db",
        type=str,
        default="nightly_checkpoint.db",
        help="For nightly mode: path to checkpoint DB",
    )
    parser.add_argument(
        "--retailer",
        type=str,
        default="talron",
        choices=available_retailers,
        help=f"Target retailer strategy ({', '.join(available_retailers)}). Default: talron",
    )
    parser.add_argument("--concurrency", type=int, default=15, help="Number of async workers (default: 15)")
    parser.add_argument("--jitter", type=int, nargs=2, default=[10, 40], help="Min and Max jitter delay in ms (default: 10 40)")
    parser.add_argument("--leetspeak", action="store_true", help="Generate leetspeak mutations (e.g. t4lron, w3lcom3)")
    parser.add_argument("--wordlist", type=str, default=None, help="Custom wordlist file to append to candidates")
    parser.add_argument(
        "--stack-test",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically test coupon stacking logic (default: True)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on maximum number of candidates to test")
    parser.add_argument("--nonce", type=str, default=None, help="Optional override for security nonce")
    parser.add_argument("--cookie", type=str, default=None, help="Optional raw cookie header string override")
    parser.add_argument("--url", type=str, default=None, help="Optional override for target API endpoint URL")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # 1. Dispatch to Nightly Pipeline if requested
    if getattr(args, "subcommand", None) == "nightly" or getattr(args, "nightly", False):
        raw_retailers = getattr(args, "retailers", "all")
        retailer_list = [r.strip() for r in raw_retailers.split(",") if r.strip()]
        pipeline = NightlyPipeline(
            retailer_names=retailer_list,
            concurrency_per_retailer=args.concurrency,
            target_rps_per_retailer=getattr(args, "rate_limit", 6.0),
            proxy_file=getattr(args, "proxies", None),
            resume=getattr(args, "resume", True),
            limit=args.limit,
            include_leetspeak=getattr(args, "leetspeak", True),
            db_path=getattr(args, "checkpoint_db", "nightly_checkpoint.db"),
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
        return

    # 2. Instantiate Retailer Strategy for Single Target Run
    strategy = get_retailer_strategy(args.retailer)

    # 3. Ingest Custom Wordlist Seeds
    custom_seeds = []
    if args.wordlist and Path(args.wordlist).is_file():
        print(f"[*] Ingesting custom wordlist from: {args.wordlist}", flush=True)
        with open(args.wordlist, "r", encoding="utf-8", errors="ignore") as f:
            custom_seeds = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # 4. Generate Permutations using Strategy Domain Rules
    candidates = WordlistEngine.generate_candidates(
        strategy=strategy,
        include_leetspeak=args.leetspeak,
        custom_seeds=custom_seeds,
    )
    if args.limit and args.limit > 0:
        candidates = candidates[:args.limit]

    # 5. Resolve Overrides (Cookies, Nonce, URL)
    cookies_override = parse_cookie_string(args.cookie) if args.cookie else None

    # 6. Engine Setup
    engine = Engine(
        strategy=strategy,
        url=args.url,
        cookies=cookies_override,
        security_nonce=args.nonce,
        concurrency=args.concurrency,
        jitter_ms=(args.jitter[0], args.jitter[1]),
        timeout=10.0,
    )

    # 7. Execution
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        findings = loop.run_until_complete(engine.execute_fuzz(candidates))

        # 8. Stacking Logic Verification
        stacking_res = {}
        if args.stack_test and findings:
            valid_codes = [f.code for f in findings if f.is_valid]
            if len(valid_codes) >= 2:
                stacking_res = loop.run_until_complete(engine.test_stacking(valid_codes))

        # 9. Reporting
        print_conclusion(
            strategy=strategy,
            findings=findings,
            stats=engine.stats,
            stacking_result=stacking_res,
            active_url=engine.url,
            active_nonce=engine.security_nonce,
        )

    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by operator (SIGINT). Exiting cleanly...", flush=True)
        if engine.stats["start_time"] > 0 and engine.stats["end_time"] == 0.0:
            engine.stats["end_time"] = time.perf_counter()
        print_conclusion(
            strategy=strategy,
            findings=engine.findings,
            stats=engine.stats,
            stacking_result={},
            active_url=engine.url,
            active_nonce=engine.security_nonce,
        )
    finally:
        loop.close()


if __name__ == "__main__":
    main()

