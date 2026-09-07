import json
from models import TriageStatus
from strategies.base import BaseRetailerStrategy, clean_html


class RingerStrategy(BaseRetailerStrategy):
    """Strategy implementation for Ringers (WordPress admin-ajax matat_mini_coupon_code JSON endpoint)."""

    @property
    def name(self) -> str:
        return "ringer"

    @property
    def display_name(self) -> str:
        return "Ringers"

    @property
    def target_url(self) -> str:
        return "https://www.ringers.co.il/wp-admin/admin-ajax.php"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "*/*",
            "accept-language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.ringers.co.il",
            "priority": "u=1, i",
            "referer": "https://www.ringers.co.il/product-category/%d7%a9%d7%a2%d7%95%d7%9f-roberto-marino-%d7%9e%d7%9c%d7%91%d7%a0%d7%99-%d7%9c%d7%a0%d7%a9%d7%99%d7%9d-rm1702",
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
            "PHPSESSID": "prsecslba5nfoukcchlpu7dkq6",
            "first_visit": "1788722311",
            "anonymous_id": "6067:6ed8bd931cce15deb7dd066452578e",
            "flashy_attribution": '["direct"]',
            "pys_session_limit": "true",
            "pys_start_session": "true",
            "pys_first_visit": "true",
            "pysTrafficSource": "google.com",
            "_fbp": "fb.1.1788722311306.8207784366",
            "_gcl_au": "1.1.1613217705.1788722312",
            "_gid": "GA1.3.996282453.1788722312",
            "_dc_gtm_UA-91440680-1": "1",
            "_tt_enable_cookie": "1",
            "_ttp": "01M1W2GWXGYT94XN93H08TWK7F_.tt.2",
            "pbid": "fad0ee09908b30c2446a4462e4d65186221b42f28197464f2fbbd015d5ced39f",
            "_ga": "GA1.3.1986741593.1788722312",
            "woocommerce_items_in_cart": "1",
            "wp_woocommerce_session_7168bc6c2b0b63d023d5351c9eb5c494": "t_21cc779a2c0cc47e8fca35f5b84352||1788895119||1788891519||016aaedc035604441690aba5d6020221",
            "flashy_cart": "eyJ2YWx1ZSI6IjM5OCIsImNvbnRlbnRfaWRzIjpbODAyNjhdLCJjdXJyZW5jeSI6IklMUyJ9",
            "woocommerce_cart_hash": "c7478ed422c0bd63e94a5d1209b3a560",
            "flashy_cache": "eyJ2YWx1ZSI6IjM5OCIsImNvbnRlbnRfaWRzIjpbODAyNjhdLCJjdXJyZW5jeSI6IklMUyJ9",
            "pysAddToCartFragmentId": "c7478ed422c0bd63e94a5d1209b3a560",
        }

    @property
    def default_nonce(self) -> str:
        return "e3e143a754"

    @property
    def baseline_candidates(self) -> list[str]:
        # welcome5 is confirmed active code; dasd is confirmed invalid
        return ["welcome5", "dasd"]

    def build_payload(self, coupon: str, nonce: str) -> dict[str, str]:
        return {
            "action": "matat_mini_coupon_code",
            "coupon_code": coupon,
            "security": nonce,
        }

    def triage_response(self, text: str, status_code: int) -> tuple[bool, str, str]:
        if status_code == 429:
            return False, TriageStatus.RATE_LIMITED, "HTTP 429 Too Many Requests (Rate limit hit)"

        if status_code == 403 or text.strip() == "-1":
            return False, TriageStatus.EXPIRED_NONCE, "Security nonce or session cookie expired (HTTP 403 / -1)"

        if "cf-mitigated" in text or "challenge-running" in text or "Cloudflare" in text:
            return False, TriageStatus.WAF_CHALLENGE, "Cloudflare WAF challenge triggered"

        # In matat_mini_coupon_code, WordPress returns '0' when coupon is already in the cart session
        if text.strip() == "0":
            return True, TriageStatus.ALREADY_APPLIED, "קוד הקופון כבר הוחל בסל."

        # Parse JSON response
        try:
            data = json.loads(text)
        except Exception:
            data = None

        if isinstance(data, dict):
            # Success response
            if data.get("success") is True:
                msg = data.get("text") or "הקופון נוסף בהצלחה"
                applied_codes = data.get("coupon_code", [])
                code_str = f" ({', '.join(applied_codes)})" if applied_codes else ""
                return True, TriageStatus.APPLIED, f"{clean_html(msg)}{code_str}"

            # Error response
            if data.get("error") is True or "error_message" in data:
                raw_msg = str(data.get("error_message") or "")
                msg = clean_html(raw_msg)

                # Invalid coupon
                if any(kw in msg for kw in ["לא תקין", "לא קיים", "אינו קיים", "does not exist", "invalid"]):
                    return False, TriageStatus.INVALID, msg

                # Already applied
                if any(kw in msg for kw in ["כבר הוחל", "כבר נוסף", "already applied"]):
                    return True, TriageStatus.ALREADY_APPLIED, msg

                # Conditional / restricted
                return True, TriageStatus.RESTRICTED, f"Exists (conditional): {msg}"

        # Fallback check
        if "הקופון נוסף בהצלחה" in text:
            return True, TriageStatus.APPLIED, "הקופון נוסף בהצלחה"

        return False, TriageStatus.INVALID, f"Unknown response ({status_code}): {clean_html(text[:100])}"

    def get_brand_tokens(self) -> tuple[list[str], list[str]]:
        brand_en = ["ringers", "ringer", "roberto", "marino"]
        brand_he = ["רינגרס", "רינגר", "רוברטו", "מרינו"]
        return brand_en, brand_he

    def get_dedicated_seeds(self) -> list[str]:
        return [
            "welcome5", "welcome10", "welcome15", "welcome20",
            "ringers5", "ringers10", "ringers15", "ringers20", "ringers50",
            "ringer5", "ringer10", "ringer15", "ringer20",
            "vip", "vip10", "vip20", "club", "club10",
            "new5", "new10", "new30", "first10", "first15",
            "שעון10", "תכשיט10", "תכשיטים10", "רינגרס10", "רינגרס5"
        ]

    def get_niche_keywords(self) -> list[str]:
        # Israeli watches, jewelry, luxury boutique keywords
        return [
            "watch", "watches", "jewelry", "ring", "rings", "diamond",
            "gold", "silver", "chain", "bracelet", "clock", "luxury",
            "שעון", "שעונים", "תכשיט", "תכשיטים", "טבעת", "טבעות",
            "שרשרת", "שרשראות", "צמיד", "צמידים", "יהלום", "זהב", "כסף"
        ]

    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        return f"curl -s -X POST '{self.target_url}' -d 'action=matat_mini_coupon_code&coupon_code={coupon}&security={nonce}'"
