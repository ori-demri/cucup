import json
from models import TriageStatus
from strategies.base import BaseRetailerStrategy, clean_html


class LavidoStrategy(BaseRetailerStrategy):
    """Strategy implementation for Lavido (WordPress admin-ajax.php endpoint)."""

    @property
    def name(self) -> str:
        return "lavido"

    @property
    def display_name(self) -> str:
        return "Lavido"

    @property
    def target_url(self) -> str:
        return "https://lavido.co.il/wp-admin/admin-ajax.php"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "*/*",
            "accept-language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://lavido.co.il",
            "priority": "u=1, i",
            "referer": "https://lavido.co.il/",
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
            "woocommerce_cart_hash": "bb46dc4df97018275d3949077ef86863",
            "wp_woocommerce_session_917311572c7cfbb90289302f8cd65615": (
                "t_a5b945c6b28e3e56d115bc9d847979|1791485564|1791399164|$generic$s7vbdctIgVl4x0HMz8DAALbD-WWfGuMRX8_6NIQi"
            ),
        }

    @property
    def default_nonce(self) -> str:
        return "fb3bb54fb5"

    @property
    def baseline_candidates(self) -> list[str]:
        # oriki is a known invalid code
        return ["oriki"]

    def build_payload(self, coupon: str, nonce: str) -> dict[str, str]:
        return {
            "action": "matat_mini_coupon_code",
            "coupon_code": coupon,
            "security": nonce,
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

        if text.strip() == "-1":
            return False, TriageStatus.EXPIRED_NONCE, "Security nonce or session cookie expired (-1)"

        try:
            data = json.loads(text)
            
            if data.get("error"):
                msg = data.get("error_message", "Unknown error")
                
                if any(kw in msg for kw in ["לא תקין", "לא קיים", "אינו תקין"]):
                    return False, TriageStatus.INVALID, msg
                    
                if any(kw in msg for kw in ["כבר הוחל", "כבר נוסף", "הוזן כבר"]):
                    return True, TriageStatus.ALREADY_APPLIED, msg
                    
                return True, TriageStatus.RESTRICTED, f"Exists (conditional/error): {msg}"
            
            else:
                msg = data.get("message", "קוד הקופון הוחל בהצלחה.")
                return True, TriageStatus.APPLIED, msg
                
        except json.JSONDecodeError:
            return False, TriageStatus.INVALID, f"Unknown JSON response ({status_code}): {clean_html(text[:100])}"

    def get_brand_tokens(self) -> tuple[list[str], list[str]]:
        brand_en = ["lavido", "lavidocosmetics"]
        brand_he = ["לבידו"]
        return brand_en, brand_he

    def get_dedicated_seeds(self) -> list[str]:
        return [
            "lavido", "lavido10", "lavido15", "lavido20",
            "welcome", "welcome10", "welcome15", "first10", "vip10"
        ]

    def get_niche_keywords(self) -> list[str]:
        # Cosmetics, skincare, natural, vegan, aromatherapy
        return [
            "skincare", "natural", "organic", "vegan", "face", "body", "serum", "cream",
            "clean", "beauty", "soft", "glow", "fresh", "care", "spa", "nature",
            "טיפוח", "טבעי", "אורגני", "טבעוני", "פנים", "גוף", "סרום", "קרם",
            "נקי", "יופי", "רך", "זוהר", "רענן", "טבע", "ספא"
        ]

    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        return f"curl -s -X POST '{self.target_url}' -d 'action=matat_mini_coupon_code&security={nonce}&coupon_code={coupon}'"
