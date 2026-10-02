import random
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from businesses.models import Business
from products.models import Product
from sales.models import SalesRecord, Promotion, CompetitorPrice
from alerts.models import BusinessAlert

random.seed(42)
np.random.seed(42)

DEMO_USERNAME = "demo_owner"
DEMO_PASSWORD = "PricePulse@123"

# (name, category, base_daily_demand, current_price, weekend_heavy)
PRODUCTS = [
    ("Milk Bread", "bakery", 20, 45, False),
    ("Chocolate Cake", "bakery", 12, 450, True),
    ("Veg Sandwich", "snacks", 15, 60, True),
    ("Cappuccino", "beverages", 25, 90, True),
    ("Masala Dosa", "snacks", 18, 70, True),
    ("Fresh Juice", "beverages", 20, 65, False),
    ("Coffee Beans 250g", "grocery", 8, 320, False),
    ("Cookies Pack", "snacks", 22, 55, False),
    ("Premium Cotton Shirt", "clothing", 4, 899, False),
    ("Bluetooth Speaker", "electronics", 2, 1499, False),
    ("Paneer 200g", "dairy", 15, 80, False),
    ("Curd 400g", "dairy", 18, 40, False),
    ("Butter 100g", "dairy", 10, 55, False),
    ("Rusk Pack", "bakery", 14, 35, False),
    ("Masala Chai", "beverages", 30, 25, False),
    ("Chips Pack", "snacks", 25, 20, True),
    ("Cold Drink 750ml", "beverages", 18, 45, True),
    ("Formal Trousers", "clothing", 3, 1299, False),
    ("Wireless Earbuds", "electronics", 3, 1999, False),
    ("Vitamin C Tablets", "pharmacy", 6, 180, False),
]

COMPETITORS = ["Local Mart", "QuickBasket", "CityGrocer"]


class Command(BaseCommand):
    help = "Seed the database with a realistic demo business, products, 6 months of sales, promotions, and alerts."

    @transaction.atomic
    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username=DEMO_USERNAME, defaults={"email": "owner@sunrisebakerycafe.example"}
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
            self.stdout.write(f"Created demo login -> username: {DEMO_USERNAME} / password: {DEMO_PASSWORD}")
        else:
            self.stdout.write("Demo user already exists, reusing it.")

        business, _ = Business.objects.update_or_create(
            owner=user,
            defaults=dict(
                business_name="Sunrise Bakery & Cafe",
                owner_name="Anita Sharma",
                email="owner@sunrisebakerycafe.example",
                phone="+91 98765 43210",
                business_type="bakery",
                address="12 MG Road, Bengaluru, Karnataka",
            ),
        )

        Product.objects.filter(business=business).delete()  # clean reseed

        products = []
        for i, (name, category, base_demand, price, weekend_heavy) in enumerate(PRODUCTS):
            cost = round(price * random.uniform(0.55, 0.72), 2)
            min_price = round(price * 0.80, 2)
            max_price = round(price * 1.30, 2)
            # Vary stock so some products land in Critical/Low/Overstocked/Healthy for a realistic demo
            stock_profile = i % 4
            if stock_profile == 0:
                stock = int(base_demand * random.uniform(1.0, 2.0))     # low / critical
            elif stock_profile == 1:
                stock = int(base_demand * random.uniform(6, 10))        # healthy
            elif stock_profile == 2:
                stock = int(base_demand * random.uniform(20, 35))       # overstocked
            else:
                stock = int(base_demand * random.uniform(3, 5))         # healthy/low border

            product = Product.objects.create(
                business=business,
                product_name=name,
                category=category,
                sku=f"SKU-{i+1:04d}",
                description=f"{name} — a top seller at {business.business_name}.",
                cost_price=cost,
                current_price=price,
                minimum_price=min_price,
                maximum_price=max_price,
                stock_quantity=stock,
                reorder_level=int(base_demand * 3),
            )
            products.append((product, base_demand, weekend_heavy))

        self.stdout.write(f"Created {len(products)} products.")

        # ---- 6 months of daily sales history ----
        SalesRecord.objects.filter(business=business).delete()
        days = 182
        start_date = date.today() - timedelta(days=days)

        # Each product gets 1-2 promotion windows in the last 6 months (discounted demand boost)
        promo_windows = {}
        Promotion.objects.filter(product__in=[p for p, _, _ in products]).delete()
        for product, base_demand, _ in products:
            windows = []
            num_promos = random.choice([0, 1, 1, 2])
            for _ in range(num_promos):
                promo_start_offset = random.randint(10, days - 20)
                promo_len = random.randint(5, 14)
                p_start = start_date + timedelta(days=promo_start_offset)
                p_end = p_start + timedelta(days=promo_len)
                discount = random.choice([10, 15, 20, 25])
                windows.append((p_start, p_end, discount))
                status = "ended" if p_end < date.today() else ("active" if p_start <= date.today() <= p_end else "scheduled")
                Promotion.objects.create(
                    product=product,
                    promotion_name=f"{product.product_name} Special Offer",
                    discount_percentage=discount,
                    start_date=p_start,
                    end_date=p_end,
                    status=status,
                )
            promo_windows[product.id] = windows

        sales_records = []
        for product, base_demand, weekend_heavy in products:
            trend_drift = random.uniform(-0.05, 0.15)  # mild overall growth/decline over 6 months
            for offset in range(days):
                d = start_date + timedelta(days=offset)
                weekday = d.weekday()

                weekend_mult = 1.0
                if weekend_heavy and weekday in (5, 6):
                    weekend_mult = 1.45
                elif weekday in (5, 6):
                    weekend_mult = 1.15

                seasonal_mult = 1 + 0.15 * np.sin((d.timetuple().tm_yday / 365) * 2 * np.pi)
                progress = offset / days
                trend_mult = 1 + trend_drift * progress

                discount = 0
                for p_start, p_end, disc in promo_windows[product.id]:
                    if p_start <= d <= p_end:
                        discount = disc
                        break

                elasticity_boost = 1 + (discount / 100) * 0.9  # discounts noticeably lift demand

                noise = np.random.normal(1.0, 0.12)
                quantity = base_demand * weekend_mult * seasonal_mult * trend_mult * elasticity_boost * noise
                quantity = max(int(round(quantity)), 0)

                if quantity == 0:
                    continue

                selling_price = Decimal(str(product.current_price))
                discount_dec = Decimal(str(discount))
                net_price = selling_price * (Decimal(1) - discount_dec / Decimal(100))
                revenue = (net_price * quantity).quantize(Decimal("0.01"))

                sales_records.append(SalesRecord(
                    business=business,
                    product=product,
                    sale_date=d,
                    quantity_sold=quantity,
                    selling_price=selling_price,
                    discount_percentage=discount_dec,
                    revenue=revenue,
                ))

        # bulk_create bypasses the model's custom save(), so revenue is precomputed above.
        SalesRecord.objects.bulk_create(sales_records, batch_size=1000)

        self.stdout.write(f"Generated {len(sales_records)} sales records across {days} days.")

        # ---- Competitor prices for a subset of products ----
        CompetitorPrice.objects.filter(product__in=[p for p, _, _ in products]).delete()
        for product, _, _ in random.sample(products, k=10):
            for competitor in random.sample(COMPETITORS, k=2):
                CompetitorPrice.objects.create(
                    product=product,
                    competitor_name=competitor,
                    competitor_price=round(float(product.current_price) * random.uniform(0.9, 1.1), 2),
                    recorded_date=date.today() - timedelta(days=random.randint(0, 10)),
                )

        # ---- Demo alerts ----
        BusinessAlert.objects.filter(business=business).delete()
        sample_products = {p.product_name: p for p, _, _ in products}
        demo_alerts = [
            ("high_demand", "High Demand Expected", "warning",
             f"Demand for {products[1][0].product_name} is expected to increase significantly this weekend."),
            ("overstock", "Overstock Risk", "info",
             f"{products[6][0].product_name} has an estimated 45+ days of inventory remaining."),
            ("pricing_opportunity", "Pricing Opportunity", "info",
             f"Demand for {products[2][0].product_name} has trended upward recently. Consider a moderate price increase."),
            ("stockout", "Stockout Risk", "critical",
             f"{products[0][0].product_name} may run out within the next few days at current sales pace."),
        ]
        for alert_type, title, severity, message in demo_alerts:
            BusinessAlert.objects.create(
                business=business,
                product=None,
                alert_type=alert_type,
                title=title,
                message=message,
                severity=severity,
                is_read=random.choice([True, False]),
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed complete.\nLogin with -> username: {DEMO_USERNAME}  password: {DEMO_PASSWORD}\n"
            f"Business: {business.business_name}\n"
            "Next: run `python manage.py train_demand_model` to train the ML model."
        ))
