from abc import ABC, abstractmethod
import re


LI_REGEX = re.compile(r"<li[^>]*>(.*?)</li>", re.DOTALL | re.IGNORECASE)
TAG_CLEANER = re.compile(r"<[^>]+>")


def clean_html(raw_html: str) -> str:
    """Strips markup and unescapes standard HTML entities."""
    clean = TAG_CLEANER.sub(" ", raw_html)
    clean = (
        clean.replace("&quot;", '"')
        .replace("&#039;", "'")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return " ".join(clean.split())


class BaseRetailerStrategy(ABC):
    """Abstract Strategy interface for e-commerce coupon enumeration targets."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique retailer key (e.g. 'talron', 'orlando')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable target name."""
        pass

    @property
    @abstractmethod
    def target_url(self) -> str:
        """Target API endpoint URL."""
        pass

    @property
    @abstractmethod
    def headers(self) -> dict[str, str]:
        """Browser headers matching target profile."""
        pass

    @property
    @abstractmethod
    def default_cookies(self) -> dict[str, str]:
        """Default session cookies for baseline/probing."""
        pass

    @property
    @abstractmethod
    def default_nonce(self) -> str:
        """Default security / AJAX nonce."""
        pass

    @property
    @abstractmethod
    def baseline_candidates(self) -> list[str]:
        """High confidence sample coupons for baseline sanity verification."""
        pass

    @abstractmethod
    def build_payload(self, coupon: str, nonce: str) -> dict[str, str]:
        """Constructs form data dictionary for POST request."""
        pass

    @abstractmethod
    def triage_response(self, text: str, status_code: int) -> tuple[bool, str, str]:
        """
        Sub-millisecond response triager.
        Returns:
            tuple of (is_valid: bool, status: str, message: str)
        """
        pass

    @abstractmethod
    def get_brand_tokens(self) -> tuple[list[str], list[str]]:
        """Returns tuple of (brand_tokens_en, brand_tokens_he)."""
        pass

    @abstractmethod
    def get_dedicated_seeds(self) -> list[str]:
        """Returns high-probability retailer seed codes."""
        pass

    @abstractmethod
    def get_niche_keywords(self) -> list[str]:
        """Returns domain/industry-specific keyword vectors."""
        pass

    @abstractmethod
    def get_curl_poc(self, coupon: str, nonce: str) -> str:
        """Generates curl command for reproduction / PoC."""
        pass
