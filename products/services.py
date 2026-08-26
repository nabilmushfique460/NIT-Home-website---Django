from typing import Any, Optional
from django.db.models import Q, QuerySet
from django.core.mail import send_mail
from django.conf import settings
from .models import Product, ProductReview
from accounts.models import Notification, User

# Service encapsulating product catalog search, hardware filtering, and sorting
class ProductFilterService:

    @classmethod
    def get_filtered_products(cls, params: dict[str, Any]) -> QuerySet[Product]:
        # Pre-fetch related categories, images, and specifications for optimal query performance
        queryset = Product.objects.all().select_related('category').prefetch_related('images', 'specifications')

        # Filter by category slug
        category_slug = params.get('category', '').strip()
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Multi-word full-text search across product names, descriptions, categories, and specs
        query = params.get('q', '').strip()
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

        # Filter by brand
        brand = params.get('brand', '').strip()
        if brand:
            queryset = queryset.filter(brand__iexact=brand)

        # Filter by RAM capacity
        ram = params.get('ram', '').strip().lower()
        if ram:
            queryset = queryset.filter(ram_capacity=ram)

        # Filter by GPU dedicated VRAM
        gpu_vram = params.get('gpu_vram', '').strip().lower()
        if gpu_vram:
            queryset = queryset.filter(gpu_vram=gpu_vram)

        # Filter by SSD storage capacity
        ssd = params.get('ssd', '').strip().lower()
        if ssd:
            queryset = queryset.filter(ssd_capacity=ssd)

        # Filter by hardware generation
        generation = params.get('generation', '').strip().lower()
        if generation:
            queryset = queryset.filter(generation=generation)

        # Filter by CPU series
        cpu_series = params.get('cpu_series', '').strip().lower()
        if cpu_series:
            queryset = queryset.filter(cpu_series=cpu_series)

        # Filter by CPU minimum core count
        cpu_cores = params.get('cpu_cores', '').strip()
        if cpu_cores:
            try:
                cores_val = int(cpu_cores)
                queryset = queryset.filter(cpu_cores__gte=cores_val)
            except (ValueError, TypeError):
                pass

        # Filter by CPU minimum thread count
        cpu_threads = params.get('cpu_threads', '').strip()
        if cpu_threads:
            try:
                threads_val = int(cpu_threads)
                queryset = queryset.filter(cpu_threads__gte=threads_val)
            except (ValueError, TypeError):
                pass

        # Filter by minimum price
        min_price = params.get('min_price', '').strip()
        if min_price:
            try:
                min_p = float(min_price)
                if min_p >= 0:
                    queryset = queryset.filter(price__gte=min_p)
            except (ValueError, TypeError):
                pass

        # Filter by maximum price
        max_price = params.get('max_price', '').strip()
        if max_price:
            try:
                max_p = float(max_price)
                if max_p >= 0:
                    queryset = queryset.filter(price__lte=max_p)
            except (ValueError, TypeError):
                pass

        # Filter for in-stock items only
        in_stock = params.get('in_stock', '').strip()
        if in_stock in ('1', 'true', 'on', 'yes'):
            queryset = queryset.filter(stock_qty__gt=0)

        # Apply sorting criteria
        sort = params.get('sort', '').strip()
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

# Service handling product review submission, email notices, and notification creation
class ReviewService:

    @classmethod
    def submit_review(
        cls,
        product: Product,
        author_name: str,
        author_email: str,
        rating: int,
        title: str,
        comment: str,
        user: Optional[User] = None
    ) -> ProductReview:
        # Create product review record
        review = ProductReview.objects.create(
            product=product,
            user=user if user and user.is_authenticated else None,
            author_name=author_name,
            author_email=author_email,
            rating=rating,
            title=title,
            comment=comment,
            is_approved=True,
            is_verified_purchase=True
        )

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')

        # Send confirmation email to reviewer
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
                send_mail(
                    subject=user_subject,
                    message=user_message,
                    from_email=from_email,
                    recipient_list=[author_email],
                    fail_silently=False
                )
            except Exception:
                pass

        # Send alert email to store administrator
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
            send_mail(
                subject=admin_subject,
                message=admin_message,
                from_email=from_email,
                recipient_list=['nabil29089@gmail.com'],
                fail_silently=False
            )
        except Exception:
            pass

        # Create in-app notification for authenticated reviewers
        if user and user.is_authenticated:
            Notification.objects.create(
                user=user,
                title=f"Review Published for {product.name}",
                message=f"Thank you! Your {rating}-star review for {product.name} has been published.",
                link=f"/product/{product.slug}/"
            )

        return review
