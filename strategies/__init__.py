from strategies.base import BaseRetailerStrategy
from strategies.talron import TalronStrategy
from strategies.orlando import OrlandoStrategy
from strategies.ringer import RingerStrategy
from strategies.spring import SpringStrategy
from strategies.bobot import BobotStrategy


RETAILER_REGISTRY: dict[str, type[BaseRetailerStrategy]] = {
    "talron": TalronStrategy,
    "orlando": OrlandoStrategy,
    "ringer": RingerStrategy,
    "ringers": RingerStrategy,
    "spring": SpringStrategy,
    "avivs": SpringStrategy,
    "aviv": SpringStrategy,
    "bobot": BobotStrategy,
    "bobot-israel": BobotStrategy,
    "bobotisrael": BobotStrategy,
}


def get_retailer_strategy(name: str) -> BaseRetailerStrategy:
    """Factory function to instantiate a RetailerStrategy by name."""
    key = name.strip().lower()
    strategy_cls = RETAILER_REGISTRY.get(key)
    if not strategy_cls:
        available = ", ".join(RETAILER_REGISTRY.keys())
        raise ValueError(f"Unknown retailer '{name}'. Available retailers: {available}")
    return strategy_cls()


__all__ = [
    "BaseRetailerStrategy",
    "TalronStrategy",
    "OrlandoStrategy",
    "RingerStrategy",
    "SpringStrategy",
    "BobotStrategy",
    "RETAILER_REGISTRY",
    "get_retailer_strategy",
]
