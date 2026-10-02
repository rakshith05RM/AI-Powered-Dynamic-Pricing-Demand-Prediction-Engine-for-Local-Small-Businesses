"""
pricing/services/pricing_engine.py

A transparent, rule-based pricing layer on top of the ML demand prediction.
Responsibilities:
- Analyze predicted demand vs recent historical average demand.
- Analyze current inventory relative to predicted demand (days of cover).
- Calculate a recommended price within configurable max change limits.
- Always enforce product.minimum_price <= recommended_price <= product.maximum_price.
- Produce a human-readable reason string.
- Estimate expected revenue at the recommended price.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings


def _round_money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PricingEngine:
    def __init__(self, max_increase_pct=None, max_decrease_pct=None):
        self.max_increase_pct = max_increase_pct if max_increase_pct is not None else settings.PRICING_MAX_INCREASE_PCT
        self.max_decrease_pct = max_decrease_pct if max_decrease_pct is not None else settings.PRICING_MAX_DECREASE_PCT

    def recommend(self, product, predicted_demand, recent_avg_demand, active_promotion=None):
        """
        product: Product instance
        predicted_demand: float, predicted units for the upcoming period
        recent_avg_demand: float, recent historical average daily/period demand for comparison
        active_promotion: Promotion instance or None
        Returns dict: recommended_price, price_change_percentage, expected_revenue, reason
        """
        current_price = Decimal(product.current_price)
        min_price = Decimal(product.minimum_price)
        max_price = Decimal(product.maximum_price)

        recent_avg_demand = max(recent_avg_demand, 0.01)
        demand_ratio = predicted_demand / recent_avg_demand  # >1 = demand rising

        # Inventory pressure: how many "periods" of stock remain at the predicted demand rate.
        days_of_cover = (product.stock_quantity / predicted_demand) if predicted_demand > 0 else 999

        pct_change = 0.0
        reasons = []

        if demand_ratio >= 1.15 and days_of_cover <= 10:
            # High demand + limited inventory -> raise price, scaled by how strong the signal is
            strength = min((demand_ratio - 1.0), 0.5)  # cap scaling input
            pct_change = min(strength * 30, self.max_increase_pct)  # e.g. up to max cap
            reasons.append(
                f"Predicted demand is {round((demand_ratio - 1) * 100)}% above the recent average "
                f"while only about {days_of_cover:.1f} days of inventory remain."
            )
        elif demand_ratio >= 1.15:
            # High demand, healthy inventory -> smaller increase
            pct_change = min((demand_ratio - 1.0) * 15, self.max_increase_pct)
            reasons.append(
                f"Predicted demand is {round((demand_ratio - 1) * 100)}% above the recent average."
            )
        elif demand_ratio <= 0.85 and days_of_cover > 20:
            # Low demand + excess inventory -> discount to move stock
            weakness = min((1.0 - demand_ratio), 0.5)
            pct_change = -min(weakness * 30, self.max_decrease_pct)
            reasons.append(
                f"Predicted demand is {round((1 - demand_ratio) * 100)}% below the recent average "
                f"with roughly {days_of_cover:.0f} days of inventory on hand."
            )
        elif demand_ratio <= 0.85:
            pct_change = -min((1.0 - demand_ratio) * 12, self.max_decrease_pct)
            reasons.append(
                f"Predicted demand is {round((1 - demand_ratio) * 100)}% below the recent average."
            )
        else:
            reasons.append("Predicted demand is close to the recent average, so the current price looks appropriate.")

        if active_promotion is not None:
            reasons.append(
                f"An active promotion ('{active_promotion.promotion_name}', "
                f"-{active_promotion.discount_percentage}%) was factored into demand expectations."
            )
            # A promotion is already discounting the product; avoid stacking a further increase on top.
            pct_change = min(pct_change, 0)

        recommended_price = current_price * (Decimal(1) + Decimal(pct_change) / Decimal(100))
        recommended_price = _round_money(recommended_price)

        # Always clamp to the product's configured min/max bounds.
        clamped = False
        if recommended_price < min_price:
            recommended_price = min_price
            clamped = True
        if recommended_price > max_price:
            recommended_price = max_price
            clamped = True
        if clamped:
            reasons.append("The recommendation was capped to stay within the product's allowed price range.")

        actual_pct_change = float(((recommended_price - current_price) / current_price) * 100) if current_price else 0.0
        expected_revenue = _round_money(Decimal(predicted_demand) * recommended_price)

        direction = "increase" if actual_pct_change > 0.1 else ("decrease" if actual_pct_change < -0.1 else "no change")
        summary = {
            "increase": f"A price increase of about {actual_pct_change:.1f}% is recommended.",
            "decrease": f"A price decrease of about {abs(actual_pct_change):.1f}% is recommended.",
            "no change": "Keeping the current price is recommended.",
        }[direction]
        reasons.append(summary)

        return {
            "recommended_price": recommended_price,
            "price_change_percentage": round(actual_pct_change, 2),
            "expected_revenue": expected_revenue,
            "reason": " ".join(reasons),
        }
