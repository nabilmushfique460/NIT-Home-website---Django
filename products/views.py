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
        queryset = Product.objects.all().select_related('category').prefetch_related('images', 'specifications')

        category_slug = self.request.GET.get('category', '').strip()
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        query = self.request.GET.get('q', '').strip()
        if query:
            words = query.split()
            query_filters = Q()
            for word in words:
                query_filters &= (
                    Q(name__icontains=word) |
                    Q(brand__icontains=word) |
                    Q(short_description__icontains=word) |
                    Q(long_description__icontains=word) |
                    Q(category__name__icontains=word) |
                    Q(category__slug__icontains=word) |
                    Q(cpu_series__icontains=word) |
                    Q(gpu_vram__icontains=word) |
                    Q(ram_capacity__icontains=word) |
                    Q(ssd_capacity__icontains=word) |
                    Q(generation__icontains=word) |
                    Q(specifications__spec_name__icontains=word) |
                    Q(specifications__spec_value__icontains=word)
                )
            queryset = queryset.filter(query_filters).distinct()

        brand = self.request.GET.get('brand', '').strip()
        if brand:
            queryset = queryset.filter(brand__iexact=brand)

        # RAM Capacity Filter (8gb, 16gb, 32gb, 64gb, 128gb)
        ram = self.request.GET.get('ram', '').strip().lower()
        if ram:
            queryset = queryset.filter(ram_capacity=ram)

        # GPU VRAM Filter (8gb, 12gb, 16gb, 24gb, 32gb, 64gb, 96gb)
        gpu_vram = self.request.GET.get('gpu_vram', '').strip().lower()
        if gpu_vram:
            queryset = queryset.filter(gpu_vram=gpu_vram)

        # SSD Capacity Filter (512gb, 1tb, 2tb, 4tb, 8tb)
        ssd = self.request.GET.get('ssd', '').strip().lower()
        if ssd:
            queryset = queryset.filter(ssd_capacity=ssd)

        # Generation Filter (gen3, gen4, gen5)
        generation = self.request.GET.get('generation', '').strip().lower()
        if generation:
            queryset = queryset.filter(generation=generation)

        # CPU Series Filter (Intel i3/i5/i7/i9, AMD ryzen3/ryzen5/ryzen7/ryzen9)
        cpu_series = self.request.GET.get('cpu_series', '').strip().lower()
        if cpu_series:
            queryset = queryset.filter(cpu_series=cpu_series)

        # CPU Cores Filter (e.g. 4, 6, 8, 12, 16, 24)
        cpu_cores = self.request.GET.get('cpu_cores', '').strip()
        if cpu_cores:
            try:
                cores_val = int(cpu_cores)
                queryset = queryset.filter(cpu_cores__gte=cores_val)
            except (ValueError, TypeError):
                pass

        # CPU Threads Filter (e.g. 8, 12, 16, 24, 32)
        cpu_threads = self.request.GET.get('cpu_threads', '').strip()
        if cpu_threads:
            try:
                threads_val = int(cpu_threads)
                queryset = queryset.filter(cpu_threads__gte=threads_val)
            except (ValueError, TypeError):
                pass

        min_price = self.request.GET.get('min_price', '').strip()
        if min_price:
            try:
                min_p = float(min_price)
                if min_p >= 0:
                    queryset = queryset.filter(price__gte=min_p)
            except (ValueError, TypeError):
                pass

        max_price = self.request.GET.get('max_price', '').strip()
        if max_price:
            try:
                max_p = float(max_price)
                if max_p >= 0:
                    queryset = queryset.filter(price__lte=max_p)
            except (ValueError, TypeError):
                pass

        in_stock = self.request.GET.get('in_stock', '').strip()
        if in_stock in ('1', 'true', 'on', 'yes'):
            queryset = queryset.filter(stock_qty__gt=0)

        sort = self.request.GET.get('sort', '').strip()
        if sort == 'price_low':
            queryset = queryset.order_by('price')
        elif sort == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort == 'rating':
            queryset = queryset.order_by('-rating', '-review_count')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'name_asc':
            queryset = queryset.order_by('name')
        elif sort == 'name_desc':
            queryset = queryset.order_by('-name')
        else:
            queryset = queryset.order_by('-is_featured', '-created_at')

        return queryset

    def get_context_data(self, **kwargs):
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

        # Calculate active filters count
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
