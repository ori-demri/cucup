import re
from models import TriageStatus
from strategies.base import BaseRetailerStrategy, clean_html, LI_REGEX


class BobotStrategy(BaseRetailerStrategy):
    """Strategy implementation for Bobot Israel (WooCommerce HTML AJAX endpoint)."""

    @property
    def name(self) -> str:
        return "bobot"

    @property
    def display_name(self) -> str:
        return "Bobot Israel"

    @property
    def target_url(self) -> str:
        return "https://bobot-israel.com/?wc-ajax=apply_coupon"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "text/html, */*; q=0.01",
            "accept-language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://bobot-israel.com",
            "priority": "u=1, i",
            "referer": "https://bobot-israel.com/cart/",
            "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "x-requested-with": "XMLHttpRequest",
        }

    @property
    def default_cookies(self) -> dict[str, str]:
        return {
            "woocommerce_items_in_cart": "1",
            "woocommerce_cart_hash": "48edbef971bfeeb91c0077d548ce50da",
            "wp_woocommerce_session_cb7b1e233796718e7b138361f37e9861": (
                "t_bcd54558920e616c602a909b154f04|1788953124|1788866724|$generic$vJqSS4G40wsxczDkOsyiot1mrZXKBFOM-asPriNl"
            ),
        }

    @property
    def default_nonce(self) -> str:
        return "2ceec5b736"

    @property
    def baseline_candidates(self) -> list[str]:
        # corrin is a known valid/conditional code; dasd is confirmed invalid
        return ["corrin", "dasd"]

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
        brand_en = ["bobot", "bobot-israel", "bobotisrael"]
        brand_he = ["בובוט", "בובוט ישראל", "בובוט-ישראל"]
        return brand_en, brand_he

    def get_dedicated_seeds(self) -> list[str]:
        return [
            "corrin", "corrin10", "corrin15", "corrin20", "corrin50",
            "bobot", "bobot10", "bobot15", "bobot20", "bobot5", "bobot50", "bobot100", "bobot200",
            "בובוט", "בובוט10", "בובוט15", "בובוט20", "בובוט50",
            "welcome5", "welcome10", "welcome15", "welcome20",
            "clean10", "clean20", "robot10", "robot20", "home10",
            "vip", "vip10", "club", "club10", "first10", "first15",
        ]

    def get_niche_keywords(self) -> list[str]:
        # Robotic vacuums, stick vacuums, floor washers, window cleaners, home appliances
        return [
            "clean", "cleaner", "robot", "vacuum", "intense", "deep", "washer", "mop", "home", "pro", "pure",
            "שואב", "רובוט", "רובוטי", "שוטף", "ניקיון", "מנקה", "חלונות", "בית", "מכשירים",
        ]

    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        return f"curl -s -X POST '{self.target_url}' -d 'security={nonce}&coupon_code={coupon}'"
