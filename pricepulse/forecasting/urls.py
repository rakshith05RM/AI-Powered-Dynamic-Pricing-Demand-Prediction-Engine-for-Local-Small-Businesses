from django.urls import path
from .views import DemandForecastView, DemandPredictView, ModelRetrainView

urlpatterns = [
    path("demand/forecast/", DemandForecastView.as_view(), name="demand-forecast"),
    path("demand/predict/", DemandPredictView.as_view(), name="demand-predict"),
    path("model/retrain/", ModelRetrainView.as_view(), name="model-retrain"),
]
