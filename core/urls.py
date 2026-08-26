from django.urls import path
from .views import AboutView, ContactView

app_name = 'core'

# Core application URL routes
urlpatterns = [
    path('about/', AboutView.as_view(), name='about'),
    path('contact/', ContactView.as_view(), name='contact'),
]
