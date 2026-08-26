from typing import Any
from django.views.generic import ListView, DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse, HttpRequest
from .models import Product, Category, PromotionBanner
from .services import ProductFilterService, ReviewService

# View rendering product catalog list with search, faceted filters, and sorting
class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        return ProductFilterService.get_filtered_products(self.request.GET)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        selected_category = self.request.GET.get('category', '').strip()
        search_query = self.request.GET.get('q', '').strip()
        selected_brand = self.request.GET.get('brand', '').strip()
        selected_sort = self.request.GET.get('sort', '').strip()
        in_stock_raw = self.request.GET.get('in_stock', '').strip()
        in_stock_only = in_stock_raw in ('1', 'true', 'on', 'yes')
        min_price = self.request.GET.get('min_price', '').strip()
        max_price = self.request.GET.get('max_price', '').strip()

        selected_ram = self.request.GET.get('ram', '').strip().lower()
        selected_gpu_vram = self.request.GET.get('gpu_vram', '').strip().lower()
        selected_ssd = self.request.GET.get('ssd', '').strip().lower()
        selected_generation = self.request.GET.get('generation', '').strip().lower()
        selected_cpu_series = self.request.GET.get('cpu_series', '').strip().lower()
        selected_cpu_cores = self.request.GET.get('cpu_cores', '').strip()
        selected_cpu_threads = self.request.GET.get('cpu_threads', '').strip()

        context['categories'] = Category.objects.all()
        context['selected_category'] = selected_category
        context['search_query'] = search_query
        context['selected_brand'] = selected_brand
        context['selected_sort'] = selected_sort
        context['in_stock_only'] = in_stock_only
        context['in_stock_raw'] = in_stock_raw
        context['min_price'] = min_price
        context['max_price'] = max_price

        context['selected_ram'] = selected_ram
        context['selected_gpu_vram'] = selected_gpu_vram
        context['selected_ssd'] = selected_ssd
        context['selected_generation'] = selected_generation
        context['selected_cpu_series'] = selected_cpu_series
        context['selected_cpu_cores'] = selected_cpu_cores
        context['selected_cpu_threads'] = selected_cpu_threads

        context['ram_choices'] = Product.RAM_CAPACITY_CHOICES
        context['gpu_vram_choices'] = Product.GPU_VRAM_CHOICES
        context['ssd_choices'] = Product.SSD_CAPACITY_CHOICES
        context['generation_choices'] = Product.GENERATION_CHOICES
        context['cpu_series_choices'] = Product.CPU_SERIES_CHOICES
        context['cpu_cores_options'] = [4, 6, 8, 12, 16, 24, 32]
        context['cpu_threads_options'] = [8, 12, 16, 20, 24, 32, 64]

        context['active_banner'] = PromotionBanner.objects.filter(is_active=True).first()
        context['available_brands'] = Product.objects.values_list('brand', flat=True).distinct().order_by('brand')
        context['featured_products'] = Product.objects.filter(is_featured=True)[:4]

        # Calculate active filters count for UI filter chips
        active_filters_count = 0
        if search_query:
            active_filters_count += 1
        if selected_category:
            active_filters_count += 1
        if selected_brand:
            active_filters_count += 1
        if selected_ram:
            active_filters_count += 1
        if selected_gpu_vram:
            active_filters_count += 1
        if selected_ssd:
            active_filters_count += 1
        if selected_generation:
            active_filters_count += 1
        if selected_cpu_series:
            active_filters_count += 1
        if selected_cpu_cores:
            active_filters_count += 1
        if selected_cpu_threads:
            active_filters_count += 1
        if min_price:
            active_filters_count += 1
        if max_price:
            active_filters_count += 1
        if in_stock_only:
            active_filters_count += 1
        if selected_sort and selected_sort != 'featured':
            active_filters_count += 1

        context['active_filters_count'] = active_filters_count
        context['has_active_filters'] = active_filters_count > 0
        context['total_count'] = self.get_queryset().count()

        if selected_category:
            context['current_category_obj'] = Category.objects.filter(slug=selected_category).first()
        else:
            context['current_category_obj'] = None

        return context

# View rendering product detailed specifications, gallery, and customer feedback
class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        product = self.object
        gallery_images = list(product.images.all())

        # Fallback image array if no extra gallery images are uploaded
        if not gallery_images:
            fallback_urls = [
                product.primary_image_url,
                'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1200&auto=format&fit=crop&q=80',
                'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1200&auto=format&fit=crop&q=80'
            ]
            context['display_gallery'] = [
                {'display_url': url, 'caption': f"{product.name} Angle {i + 1}"}
                for i, url in enumerate(fallback_urls)
            ]
        else:
            context['display_gallery'] = gallery_images

        context['specifications'] = product.specifications.all()
        context['reviews'] = product.reviews.filter(is_approved=True)
        context['related_products'] = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
        return context

# View handling submission of new product reviews
class AddProductReviewView(View):

    def post(self, request: HttpRequest, slug: str, *args, **kwargs) -> HttpResponse:
        product = get_object_or_404(Product, slug=slug)
        author_name = request.POST.get('author_name', '').strip()
        author_email = request.POST.get('author_email', '').strip()
        rating_str = request.POST.get('rating', '5')
        title = request.POST.get('title', '').strip()
        comment = request.POST.get('comment', '').strip()

        # Prefill reviewer attributes from session if logged in
        if request.user.is_authenticated:
            if not author_name:
                author_name = request.user.get_full_name() or request.user.email
            if not author_email:
                author_email = request.user.email

        # Validate review inputs
        if not author_name:
            messages.error(request, 'Please provide your name for the review.')
            return redirect('products:product_detail', slug=product.slug)
        if not title:
            messages.error(request, 'Please provide a headline/title for your review.')
            return redirect('products:product_detail', slug=product.slug)
        if not comment:
            messages.error(request, 'Please write your review comment.')
            return redirect('products:product_detail', slug=product.slug)

        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                rating = 5
        except (ValueError, TypeError):
            rating = 5

        # Delegate review processing to ReviewService
        ReviewService.submit_review(
            product=product,
            author_name=author_name,
            author_email=author_email,
            rating=rating,
            title=title,
            comment=comment,
            user=request.user if request.user.is_authenticated else None
        )

        messages.success(
            request,
            'Thank you! Your verified review has been published. A confirmation email was sent to your inbox.'
        )
        return redirect('products:product_detail', slug=product.slug)
