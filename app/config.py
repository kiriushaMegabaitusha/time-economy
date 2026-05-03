"""Configuration settings for the Time Economy application.

Centralizes all magic numbers and configurable thresholds.
"""

class EconomyConfig:
    """Configuration for the time economy system."""

    CREDIT_CAP = 20
    DEFICIT_LIMIT = -10
    INITIAL_CREDIT = 5.0

    @classmethod
    def get_balance_status(cls, balance: float) -> str:
        """Determine balance status based on thresholds."""
        if balance > cls.CREDIT_CAP:
            return "hoarding"
        elif balance < cls.DEFICIT_LIMIT:
            return "deficit"
        return "healthy"

    @classmethod
    def get_alert_message(cls, name: str, balance: float, alert_type: str) -> str:
        """Generate alert message based on type."""
        if alert_type == "hoarding":
            return f"{name} has {balance} credits. Encourage spending to maintain liquidity."
        elif alert_type == "deficit":
            return f"{name} has a deficit of {abs(balance)} credits. Community check-in recommended."
        return ""