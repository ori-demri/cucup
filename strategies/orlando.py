import json
from models import TriageStatus
from strategies.base import BaseRetailerStrategy, clean_html


class OrlandoStrategy(BaseRetailerStrategy):
    """Strategy implementation for Orlando (Fast-Kart fkcart_apply_coupon JSON AJAX endpoint)."""

    @property
    def name(self) -> str:
        return "orlando"

    @property
    def display_name(self) -> str:
        return "Orlando"

    @property
    def target_url(self) -> str:
        return "https://orlando.co.il/?wc-ajax=fkcart_apply_coupon"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "*/*",
            "accept-language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://orlando.co.il",
            "priority": "u=1, i",
            "referer": "https://orlando.co.il/product/rm1702/",
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
            "_gcl_au": "1.1.795868262.1788721392",
            "wffn_traffic_source": "https://www.google.com/",
            "wffn_flt": "2026-9-6 22:03:11",
            "wffn_timezone": "Asia/Jerusalem",
            "wffn_is_mobile": "false",
            "wffn_browser": "Chrome",
            "wffn_referrer": "https://www.google.com/",
            "wffn_fl_url": "/product/rm1982/",
            "pys_session_limit": "true",
            "pys_start_session": "true",
            "pys_first_visit": "true",
            "pysTrafficSource": "google.com",
            "pys_landing_page": "https://orlando.co.il/product/rm1982/?gad_source=1&gad_campaignid=17471496869&gbraid=0AAAAADNgqFsxsPwo4cQl-S0NNRCDTDjlk&gclid=CjwKCAjwnvTUBhBoEiwAZNDxZxmIfZmgRT7jgl1Q6xqj1LvgICGetMxXY_if7_N6zhoFFrGMmzR3_hoCRYsQAvD_BwE",
            "last_pysTrafficSource": "google.com",
            "last_pys_landing_page": "https://orlando.co.il/product/rm1982/?gad_source=1&gad_campaignid=17471496869&gbraid=0AAAAADNgqFsxsPwo4cQl-S0NNRCDTDjlk&gclid=CjwKCAjwnvTUBhBoEiwAZNDxZxmIfZmgRT7jgl1Q6xqj1LvgICGetMxXY_if7_N6zhoFFrGMmzR3_hoCRYsQAvD_BwE",
            "_fbp": "fb.1.1788721392098.9604472067",
            "first_visit": "1788721392",
            "anonymous_id": "4453:566f17ba0ccfc0e9a10a1116ce201e",
            "cf_clearance": "qUAM6WwZ3TNsp7j7hbk8QG4e4GQJKeK.vXAXNZfsRSo-1788721392-1.2.1.1-oW_nLE3Gay7xYHOgXdemZdQ8bkiv1MZYKUXhpQKRwYU5TdVVP_87rBZEulgF6YCt_QzQsRpnXFvanwI3i.GY9tXFrgN45.kxSOkoLPo6dxkYuLeHWptkg0JekVDicdG3LOk06vdZ_gqUTn5BW4FAvQFGLk2ZSXFgGe90ihHdj0IcP8BpomT1P.L_QZsYzZxuyJs3KxtMEYuVd5OQPJPrXG9qexpwL8mSsOUZtVZUU64Jw9BDkDyUz2HjKubmhhB2z29KEa16xgSxpa4201THO.b_eS7PAccgNAuJeiNd7BMgCOyhInaU428SbUrjaI08XCKkK3V0ClXQorl__SruT9QPG5F2DB4NwSpg2WJLBsY",
            "_ga": "GA1.1.523513989.1788721392",
            "_tt_enable_cookie": "1",
            "_ttp": "01M1W1MV7WWFFDGEPSQJJR172K_.tt.2",
            "pbid": "9835f578e9a6289833878d5a91a08dbdace9c77ac85f316d2669bc9c53d9bc3f",
            "PHPSESSID": "fih42b5on75puoo1c18ilfr2s2",
            "_gcl_gs": "2.1.k1$i1788721397$u214725193",
            "FPGCLAW": "2.1.kCjwKCAjwnvTUBhBoEiwAZNDxZz0uw-a6-s5dUs421LmKLFMxKM_1UDWvK2RdXlOcKRUo2PtsnZVmlhoCPogQAvD_BwE$i1788721398$m1",
            "wffn_gclid": "CjwKCAjwnvTUBhBoEiwAZNDxZz0uw-a6-s5dUs421LmKLFMxKM_1UDWvK2RdXlOcKRUo2PtsnZVmlhoCPogQAvD_BwE",
            "_gcl_aw": "GCL.1788721399.CjwKCAjwnvTUBhBoEiwAZNDxZz0uw-a6-s5dUs421LmKLFMxKM_1UDWvK2RdXlOcKRUo2PtsnZVmlhoCPogQAvD_BwE",
            "flashy_attribution": '["direct x 2"]',
            "fkcart_cart_qty": "1",
            "wfocu_si": "3f6be73ef787be98f4130a7e6cfd6cdf",
            "woocommerce_items_in_cart": "1",
            "woocommerce_cart_hash": "0a5c30a66425e0162c87b694f799a64c",
            "flashy_cart": "eyJ2YWx1ZSI6IjQxOSIsImNvbnRlbnRfaWRzIjpbMzE5MTJdLCJjdXJyZW5jeSI6IklMUyJ9",
            "wp_woocommerce_session_91dc8d5bb3fb4812edf94a1e63f04a06": "t_24a50be699fb53123ba04805a08a1b|1788894203|1788807803|$generic$e6IUrPfMVanVSnalhLbrlS2kNpeY33HTxk0qbvSw",
            "pysAddToCartFragmentId": "0a5c30a66425e0162c87b694f799a64c",
            "flashy_cache": "eyJ2YWx1ZSI6IjQxOSIsImNvbnRlbnRfaWRzIjpbMzE5MTJdLCJjdXJyZW5jeSI6IklMUyJ9",
            "fkcart_cart_total": "%3Cspan+class%3D%22woocommerce-Price-amount+amount%22%3E%3Cbdi%3E419%26nbsp%3B%3Cspan+class%3D%22woocommerce-Price-currencySymbol%22%3E%26%238362%3B%3C%2Fspan%3E%3C%2Fbdi%3E%3C%2Fspan%3E",
            "_ga_Z7NBKE5N37": "GS2.1.s1788721392$o1$g1$t1788721428$j24$l0$h1464723094$dl4sKJbO40UpLdDdeZF8W4lvhxaKEeQl8Ww",
            "ttcsid": "1788721392902::FeoFFIZ1dDS-l1qXCsMY.1.1788721431683.0::1.5096.6206::38777.10.1006.730::22045.3.0",
            "ttcsid_C6OVGNS48LJ6QNNJB32G": "1788721392901::PUI01XMT9fTZPl1wqPy5.1.1788721431683.1",
        }

    @property
    def default_nonce(self) -> str:
        return "6d5c7725da"

    @property
    def baseline_candidates(self) -> list[str]:
        # new30 and welcome5 are confirmed live active codes; dasd is confirmed invalid
        return ["new30", "welcome5", "dasd"]

    def build_payload(self, coupon: str, nonce: str) -> dict[str, str]:
        return {
            "discount_code": coupon,
            "nonce": nonce,
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

        # Fast-Kart fkcart_apply_coupon returns JSON
        try:
            data = json.loads(text)
        except Exception:
            data = None

        if isinstance(data, dict):
            # Check for nonce invalidation or session errors in JSON
            if data.get("code") == 403 or data.get("message") == "Invalid nonce":
                return False, TriageStatus.EXPIRED_NONCE, "Invalid or expired nonce"

            # Check for Fast-Kart success response
            is_success = data.get("status") is True or data.get("code") == 200
            if is_success:
                raw_msg = data.get("message") or data.get("msg") or "קוד קופון הוחל בהצלחה."
                return True, TriageStatus.APPLIED, clean_html(str(raw_msg))

            # Fast-Kart error response (code 400 or status False)
            raw_msg = str(data.get("msg") or data.get("message") or "")
            msg = clean_html(raw_msg)

            # Non-existent coupon code
            if any(kw in msg for kw in ["לא קיים", "אינו קיים"]) or "does not exist" in msg.lower():
                return False, TriageStatus.INVALID, msg

            # Already applied
            if any(kw in msg for kw in ["כבר הוחל", "כבר נוסף"]) or "already applied" in msg.lower():
                return True, TriageStatus.ALREADY_APPLIED, msg

            # Conditional validity (min purchase, specific products, expired, etc.)
            return True, TriageStatus.RESTRICTED, f"Exists (conditional): {msg}"

        # Fallback for unexpected non-JSON responses
        if "קוד קופון הוחל בהצלחה" in text:
            return True, TriageStatus.APPLIED, "קוד קופון הוחל בהצלחה."

        return False, TriageStatus.INVALID, f"Unknown response ({status_code}): {clean_html(text[:100])}"

    def get_brand_tokens(self) -> tuple[list[str], list[str]]:
        brand_en = ["orlando", "orland", "orl"]
        brand_he = ["אורלנדו", "אורלנד", "אור"]
        return brand_en, brand_he

    def get_dedicated_seeds(self) -> list[str]:
        return [
            "new30", "welcome5", "welcome10", "welcome15", "welcome20",
            "orlando5", "orlando10", "orlando15", "orlando20", "orlando30", "orlando50",
            "vip", "vip10", "vip20", "club", "club10",
            "new5", "new10", "new20", "first10", "first15",
            "בושם10", "בשמים10", "בוטיק10", "אורלנדו10", "אורלנדו5"
        ]

    def get_niche_keywords(self) -> list[str]:
        # Israeli perfume, fragrance, and cosmetics boutique keywords
        return [
            "perfume", "perfumes", "fragrance", "fragrances", "scent",
            "tester", "testers", "boutique", "beauty", "cosmetics",
            "parfum", "cologne", "luxury", "glam",
            "בושם", "בשמים", "טסטר", "טסטרים", "קוסמטיקה",
            "ביוטי", "ניחוח", "ניחוחות", "ריח", "בוטיק"
        ]

    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        return f"curl -s -X POST '{self.target_url}' -d 'discount_code={coupon}&nonce={nonce}'"
