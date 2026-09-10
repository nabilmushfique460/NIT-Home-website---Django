from django.urls import path
from .views import OwnerDashboardView

app_name = 'dashboard'

urlpatterns = [
    path('', OwnerDashboardView.as_view(), name='overview'),
]
