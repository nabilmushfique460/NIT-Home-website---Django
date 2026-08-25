from django.urls import path
from .views import ProductListView, ProductDetailView, AddProductReviewView
app_name = 'products'
urlpatterns = [path('', ProductListView.as_view(), name='product_list'), path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'), path('product/<slug:slug>/review/', AddProductReviewView.as_view(), name='add_review')]
