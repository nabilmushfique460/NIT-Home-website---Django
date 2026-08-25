from django.views.generic import ListView, DetailView, View
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import Product, Category, ProductImage, PromotionBanner, ProductReview
from accounts.models import Notification

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.all().select_related('category').prefetch_related('images')
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(brand__icontains=query) | Q(short_description__icontains=query) | Q(category__name__icontains=query))
        brand = self.request.GET.get('brand')
        if brand:
            queryset = queryset.filter(brand__iexact=brand)
        in_stock = self.request.GET.get('in_stock')
        if in_stock == '1':
            queryset = queryset.filter(stock_qty__gt=0)
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
        context['active_banner'] = PromotionBanner.objects.filter(is_active=True).first()
        context['available_brands'] = Product.objects.values_list('brand', flat=True).distinct().order_by('brand')
        context['featured_products'] = Product.objects.filter(is_featured=True)[:4]
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        gallery_images = list(product.images.all())
        if not gallery_images:
            fallback_urls = [product.primary_image_url, 'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=1200&auto=format&fit=crop&q=80', 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1200&auto=format&fit=crop&q=80']
            context['display_gallery'] = [{'display_url': url, 'caption': f'{product.name} Angle {i + 1}'} for i, url in enumerate(fallback_urls)]
        else:
            context['display_gallery'] = gallery_images
        context['specifications'] = product.specifications.all()
        context['reviews'] = product.reviews.filter(is_approved=True)
        context['related_products'] = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
        return context

class AddProductReviewView(View):

    def post(self, request, slug, *args, **kwargs):
        product = get_object_or_404(Product, slug=slug)
        author_name = request.POST.get('author_name', '').strip()
        author_email = request.POST.get('author_email', '').strip()
        rating_str = request.POST.get('rating', '5')
        title = request.POST.get('title', '').strip()
        comment = request.POST.get('comment', '').strip()
        if request.user.is_authenticated:
            if not author_name:
                author_name = request.user.get_full_name() or request.user.email
            if not author_email:
                author_email = request.user.email
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

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')

        if author_email:
            user_subject = f"[N-IT HOME] Thank you for reviewing {product.name}!"
            user_message = (
                f"Dear {author_name},\n\n"
                f"Thank you for sharing your feedback on {product.name}! Your review has been published.\n\n"
                f"Your Rating: {rating} / 5 Stars\n"
                f"Headline: {title}\n"
                f"Review:\n{comment}\n\n"
                f"We truly appreciate your review and support for N-IT HOME!\n\n"
                f"Best regards,\n"
                f"N-IT HOME Team"
            )
            try:
                send_mail(subject=user_subject, message=user_message, from_email=from_email, recipient_list=[author_email], fail_silently=False)
            except Exception:
                pass

        admin_subject = f"[N-IT HOME Review Alert] New Review on {product.name}"
        admin_message = (
            f"A customer has submitted a product review on N-IT HOME:\n\n"
            f"Product: {product.name}\n"
            f"Reviewer: {author_name} ({author_email})\n"
            f"Rating: {rating} / 5 Stars\n"
            f"Headline: {title}\n\n"
            f"Review Content:\n"
            f"{comment}"
        )
        try:
            send_mail(subject=admin_subject, message=admin_message, from_email=from_email, recipient_list=['nabil29089@gmail.com'], fail_silently=False)
        except Exception:
            pass

        if request.user.is_authenticated:
            Notification.objects.create(
                user=request.user,
                title=f"Review Published for {product.name}",
                message=f"Thank you! Your {rating}-star review for {product.name} has been published.",
                link=f"/product/{product.slug}/"
            )

        messages.success(request, 'Thank you! Your verified review has been published. A confirmation email was sent to your inbox.')
        return redirect('products:product_detail', slug=product.slug)
