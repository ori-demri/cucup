import asyncio
import sys

from strategies import get_retailer_strategy
from engine import Engine

async def run_targeted_test():
    strategy = get_retailer_strategy("lavido")
    
    brand_en, brand_he = strategy.get_brand_tokens()
    brands = [b.lower() for b in brand_en]
    brands_he = brand_he
    niche_tokens = strategy.get_niche_keywords()
    
    core_nums = [10, 15, 20, 5, 25, 30, 40, 50]
    years_short = ["24", "25", "26"]
    years_full = ["2024", "2025", "2026"]
    all_years = years_short + years_full

    raw_candidates = []
    
    for b in brands:
        raw_candidates.append(b)
        for num in core_nums:
            raw_candidates.append(f"{b}{num}")
            raw_candidates.append(f"{b}-{num}")
            raw_candidates.append(f"{b}_{num}")
        for y in all_years:
            raw_candidates.append(f"{b}{y}")
            raw_candidates.append(f"{b}-{y}")
            
    for hb in brands_he:
        raw_candidates.append(hb)
        for num in core_nums:
            raw_candidates.append(f"{hb}{num}")
            raw_candidates.append(f"{hb}-{num}")
            raw_candidates.append(f"{hb}_{num}")
        for y in all_years:
            raw_candidates.append(f"{hb}{y}")
            raw_candidates.append(f"{hb}-{y}")
            
    for n in niche_tokens:
        raw_candidates.append(n)
        for p in core_nums:
            raw_candidates.append(f"{n}{p}")
            raw_candidates.append(f"{n}-{p}")
        for y in all_years:
            raw_candidates.append(f"{n}{y}")
            raw_candidates.append(f"{n}-{y}")

    # Remove duplicates
    seen = set()
    deduped = []
    for c in raw_candidates:
        code = c.strip().lower().replace(" ", "")
        if code and code not in seen:
            seen.add(code)
            deduped.append(code)

    print(f"Targeted wordlist size: {len(deduped)}")
    
    engine = Engine(
        strategy=strategy,
        concurrency=10,
        jitter_ms=(10, 40),
    )
    
    print("Starting targeted test...")
    findings = await engine.execute_fuzz(deduped)
    
    print("\n--- Findings ---")
    for f in findings:
        print(f"[{f.status.name}] {f.coupon} -> {f.message}")

if __name__ == "__main__":
    asyncio.run(run_targeted_test())
