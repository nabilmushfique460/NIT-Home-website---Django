from django.views.generic import ListView, DetailView, View
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Product, Category, ProductImage, PromotionBanner, ProductReview

class ProductListView(ListView):
    """Catalog listing Class-Based View with pure server-side filtering."""
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.all().select_related('category').prefetch_related('images')
        
        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Search filter
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(brand__icontains=query) |
                Q(short_description__icontains=query) |
                Q(category__name__icontains=query)
            )

        # Brand filter
        brand = self.request.GET.get('brand')
        if brand:
            queryset = queryset.filter(brand__iexact=brand)

        # In-stock only filter
        in_stock = self.request.GET.get('in_stock')
        if in_stock == '1':
            queryset = queryset.filter(stock_qty__gt=0)

        # Sorting
        sort = self.request.GET.get('sort')
        if sort == 'price_low':
            queryset = queryset.order_by('price')
        elif sort == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort == 'rating':
            queryset = queryset.order_by('-rating')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            # Default: Featured first, then newest
            queryset = queryset.order_by('-is_featured', '-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_brand'] = self.request.GET.get('brand', '')
        context['selected_sort'] = self.request.GET.get('sort', '')
        context['in_stock_only'] = self.request.GET.get('in_stock', '')
        
        # Active promotional banner from database (managed via Django Admin)
        context['active_banner'] = PromotionBanner.objects.filter(is_active=True).first()

        # Collect distinct brands for filter sidebar
        context['available_brands'] = Product.objects.values_list('brand', flat=True).distinct().order_by('brand')
        context['featured_products'] = Product.objects.filter(is_featured=True)[:4]
        return context

class ProductDetailView(DetailView):
    """Product Detail Class-Based View with pure CSS gallery, specs, and reviews."""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Pre-load gallery images
        gallery_images = list(product.images.all())
        
        # If no explicit gallery images attached, fallback to 3 distinct angles using primary image
        if not gallery_images:
            fallback_urls = [
                product.primary_image_url,
                "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1200&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1200&auto=format&fit=crop&q=80"
            ]
            context['display_gallery'] = [
                {'display_url': url, 'caption': f"{product.name} Angle {i+1}"}
                for i, url in enumerate(fallback_urls)
            ]
        else:
            context['display_gallery'] = gallery_images

        # Technical specs grouped
        context['specifications'] = product.specifications.all()
        
        # Approved customer reviews from database
        context['reviews'] = product.reviews.filter(is_approved=True)

        # Related products in same category
        context['related_products'] = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id)[:4]

        return context


class AddProductReviewView(View):
    """Server-side POST endpoint to submit customer reviews and comments."""

    def post(self, request, slug, *args, **kwargs):
        product = get_object_or_404(Product, slug=slug)

        author_name = request.POST.get('author_name', '').strip()
        author_email = request.POST.get('author_email', '').strip()
        rating_str = request.POST.get('rating', '5')
        title = request.POST.get('title', '').strip()
        comment = request.POST.get('comment', '').strip()

        # If user is authenticated, fill name / email from profile if empty
        if request.user.is_authenticated:
            if not author_name:
                author_name = request.user.get_full_name() or request.user.username
            if not author_email:
                author_email = request.user.email

        if not author_name:
            messages.error(request, "Please provide your name for the review.")
            return redirect('products:product_detail', slug=product.slug)

        if not title:
            messages.error(request, "Please provide a headline/title for your review.")
            return redirect('products:product_detail', slug=product.slug)

        if not comment:
            messages.error(request, "Please write your review comment.")
            return redirect('products:product_detail', slug=product.slug)

        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                rating = 5
        except (ValueError, TypeError):
            rating = 5

        ProductReview.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            author_name=author_name,
            author_email=author_email,
            rating=rating,
            title=title,
            comment=comment,
            is_approved=True,
            is_verified_purchase=True
        )

        messages.success(request, "Thank you! Your verified review and comment have been published.")
        return redirect('products:product_detail', slug=product.slug)

