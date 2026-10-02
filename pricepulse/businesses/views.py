from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg
from django.shortcuts import render, redirect

from .forms import RegistrationForm, BusinessForm
from .models import Business
from products.models import Product
from sales.models import SalesRecord
from forecasting.models import ModelMetadata
from alerts.models import BusinessAlert


def landing(request):
    return render(request, "landing.html")

def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard_overview")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            login(request, user)
            messages.success(request, f"Account created successfully. Welcome, {user.username}!")
            return redirect("business_create")
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        form = RegistrationForm()
    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_overview")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        if not username or not password:
            messages.error(request, "Please enter both your username and password.")
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                if hasattr(user, "business"):
                    return redirect("dashboard_overview")
                return redirect("business_create")
            else:
                messages.error(request, "That username or password isn't right. Please check and try again.")

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("landing")


@login_required
def create_business(request):
    if hasattr(request.user, "business"):
        return redirect("dashboard_overview")

    if request.method == "POST":
        form = BusinessForm(request.POST)
        if form.is_valid():
            business = form.save(commit=False)
            business.owner = request.user
            business.save()
            messages.success(request, "Business profile created. Welcome to PricePulse!")
            return redirect("dashboard_overview")
    else:
        form = BusinessForm(initial={"owner_name": request.user.get_full_name() or request.user.username,
                                      "email": request.user.email})
    return render(request, "auth/onboarding.html", {"form": form})


@login_required
def require_business(request):
    """Helper: redirect to onboarding if the logged-in user has no business yet."""
    if not hasattr(request.user, "business"):
        return redirect("business_create")
    return None


@login_required
def dashboard_overview(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp

    business = request.user.business
    today = date.today()
    since_7 = today - timedelta(days=7)
    since_prev_7 = today - timedelta(days=14)

    today_revenue = SalesRecord.objects.filter(business=business, sale_date=today).aggregate(s=Sum("revenue"))["s"] or 0
    week_revenue = SalesRecord.objects.filter(business=business, sale_date__gte=since_7).aggregate(s=Sum("revenue"))["s"] or 0
    prev_week_revenue = SalesRecord.objects.filter(
        business=business, sale_date__gte=since_prev_7, sale_date__lt=since_7
    ).aggregate(s=Sum("revenue"))["s"] or 0

    revenue_growth = round(((week_revenue - prev_week_revenue) / prev_week_revenue) * 100, 1) if prev_week_revenue else 0.0

    low_stock_count = sum(
        1 for p in Product.objects.filter(business=business) if p.stock_quantity <= p.reorder_level
    )

    has_model = ModelMetadata.objects.filter(business=business).exists()
    unread_alerts = BusinessAlert.objects.filter(business=business, is_read=False).count()
    product_count = Product.objects.filter(business=business).count()
    sales_count = SalesRecord.objects.filter(business=business).count()

    context = {
        "business": business,
        "today_revenue": today_revenue,
        "week_revenue": week_revenue,
        "revenue_growth": revenue_growth,
        "low_stock_count": low_stock_count,
        "has_model": has_model,
        "unread_alerts": unread_alerts,
        "product_count": product_count,
        "sales_count": sales_count,
        "active_page": "overview",
    }
    return render(request, "dashboard/overview.html", context)


@login_required
def dashboard_products(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    return render(request, "dashboard/products.html", {"business": request.user.business, "active_page": "products"})


@login_required
def dashboard_sales(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    products = Product.objects.filter(business=request.user.business)
    return render(request, "dashboard/sales.html", {
        "business": request.user.business, "active_page": "sales", "products": products,
    })


@login_required
def dashboard_forecast(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    products = Product.objects.filter(business=request.user.business)
    has_model = ModelMetadata.objects.filter(business=request.user.business).exists()
    return render(request, "dashboard/forecast.html", {
        "business": request.user.business, "active_page": "forecast", "products": products, "has_model": has_model,
    })


@login_required
def dashboard_pricing(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    products = Product.objects.filter(business=request.user.business)
    has_model = ModelMetadata.objects.filter(business=request.user.business).exists()
    return render(request, "dashboard/pricing.html", {
        "business": request.user.business, "active_page": "pricing", "products": products, "has_model": has_model,
    })


@login_required
def dashboard_inventory(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    return render(request, "dashboard/inventory.html", {"business": request.user.business, "active_page": "inventory"})


@login_required
def dashboard_alerts(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    return render(request, "dashboard/alerts.html", {"business": request.user.business, "active_page": "alerts"})


@login_required
def dashboard_analytics(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    return render(request, "dashboard/analytics.html", {"business": request.user.business, "active_page": "analytics"})


@login_required
def dashboard_model(request):
    redirect_resp = require_business(request)
    if redirect_resp:
        return redirect_resp
    metadata = ModelMetadata.objects.filter(business=request.user.business).first()
    return render(request, "dashboard/model.html", {
        "business": request.user.business, "active_page": "model", "metadata": metadata,
    })
