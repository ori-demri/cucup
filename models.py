from typing import NamedTuple


class TriageStatus:
    APPLIED = "APPLIED_SUCCESS"            # Coupon actively accepted
    ALREADY_APPLIED = "ALREADY_APPLIED"    # Coupon is valid and in active cart
    RESTRICTED = "RESTRICTED"              # Exists, but conditional (min spend, expired, etc.)
    INVALID = "INVALID_NOT_FOUND"          # Non-existent coupon
    EXPIRED_NONCE = "EXPIRED_NONCE"        # Nonce / Session invalid
    RATE_LIMITED = "RATE_LIMITED"          # HTTP 429 / WAF throttling
    WAF_CHALLENGE = "WAF_CHALLENGE"        # Cloudflare / LiteSpeed CAPTCHA
    NETWORK_ERROR = "NETWORK_ERROR"        # Timeout / connection failure


class CouponFinding(NamedTuple):
    code: str
    is_valid: bool
    status: str
    message: str
    http_status: int
    response_time_ms: float
    timestamp: str
