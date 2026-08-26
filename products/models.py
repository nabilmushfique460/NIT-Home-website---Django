from decimal import Decimal
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.conf import settings

# Model storing homepage promotional hero banners and featured showcase hardware
class PromotionBanner(models.Model):
    title = models.CharField(max_length=200, default='Unleash Peak Performance with N-IT Home')
    title_highlight = models.CharField(max_length=100, default='N-IT Home', blank=True, help_text='Part of the title to highlight')
    badge_1 = models.CharField(max_length=80, default='Next-Gen Components')
    badge_2 = models.CharField(max_length=80, default='In Stock & Ready to Ship')
    lead_text = models.TextField(
        default='Explore authentic high-performance desktop hardware — flagship NVIDIA & AMD graphics cards, '
                'AMD Ryzen 3D V-Cache processors, PCIe Gen5 NVMe storage, and low-latency DDR5 memory kits.'
    )
    perk_1 = models.CharField(max_length=80, default='Official Warranty')
    perk_2 = models.CharField(max_length=80, default='Same-Day Processing')
    perk_3 = models.CharField(max_length=80, default='bKash / Nagad / COD')
    card_tag = models.CharField(max_length=80, default='TOP SELLING FLAGSHIP')
    card_title = models.CharField(max_length=120, default='GeForce RTX 4090 24GB')
    card_price = models.DecimalField(max_digits=10, decimal_places=2, default=1699.99)
    card_link = models.CharField(max_length=255, default='/product/nvidia-geforce-rtx-4090-24gb-founders-edition/', help_text='URL or relative link for the promo button')
    card_button_text = models.CharField(max_length=80, default='View Flagship Hardware →')
    is_active = models.BooleanField(default=True, help_text='Check to display this banner on the homepage. Uncheck to hide it.')
    order = models.PositiveSmallIntegerField(default=0, help_text='Ordering priority (0 is highest priority)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Promotion Banner'
        verbose_name_plural = 'Promotion Banners'

    def __str__(self) -> str:
        status = 'Active' if self.is_active else 'Hidden'
        return f"{self.title} ({status})"

# Model representing hardware categories (e.g. GPUs, Processors, Memory, Storage)
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    icon_svg = models.TextField(blank=True, help_text='Inline SVG or icon representation')

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse('products:product_list') + f'?category={self.slug}'

    def __str__(self) -> str:
        return self.name

# Model representing hardware products and their core technical specifications
class Product(models.Model):
    RAM_CAPACITY_CHOICES = [
        ('8gb', '8GB'),
        ('16gb', '16GB'),
        ('32gb', '32GB'),
        ('64gb', '64GB'),
        ('128gb', '128GB'),
    ]

    GPU_VRAM_CHOICES = [
        ('8gb', '8GB'),
        ('12gb', '12GB'),
        ('16gb', '16GB'),
        ('24gb', '24GB'),
        ('32gb', '32GB'),
        ('64gb', '64GB'),
        ('96gb', '96GB'),
    ]

    SSD_CAPACITY_CHOICES = [
        ('512gb', '512GB'),
        ('1tb', '1TB'),
        ('2tb', '2TB'),
        ('4tb', '4TB'),
        ('8tb', '8TB'),
    ]

    GENERATION_CHOICES = [
        ('gen3', 'Gen 3 (PCIe 3.0 / DDR3)'),
        ('gen4', 'Gen 4 (PCIe 4.0 / DDR4)'),
        ('gen5', 'Gen 5 (PCIe 5.0 / DDR5)'),
    ]

    CPU_SERIES_CHOICES = [
        ('i3', 'Intel Core i3'),
        ('i5', 'Intel Core i5'),
        ('i7', 'Intel Core i7'),
        ('i9', 'Intel Core i9'),
        ('ryzen3', 'AMD Ryzen 3'),
        ('ryzen5', 'AMD Ryzen 5'),
        ('ryzen7', 'AMD Ryzen 7'),
        ('ryzen9', 'AMD Ryzen 9'),
        ('snapdragon', 'Qualcomm Snapdragon'),
        ('other', 'Other / Workstation'),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_qty = models.PositiveIntegerField(default=10)
    short_description = models.TextField(max_length=500, help_text='Short teaser shown in listing cards')
    long_description = models.TextField(help_text='Detailed markdown/HTML rich description with performance specs')
    thumbnail = models.ImageField(upload_to='products/thumbs/', blank=True, null=True)
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True, help_text='CDN or web fallback image')
    video_url = models.URLField(max_length=500, blank=True, null=True, help_text='Direct MP4 video stream URL')
    is_featured = models.BooleanField(default=False)
    warranty = models.CharField(max_length=100, default='3 Years Manufacturer Warranty')
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.9)
    review_count = models.PositiveIntegerField(default=48)

    # Granular hardware specification fields for filtering and sorting
    ram_capacity = models.CharField(max_length=20, choices=RAM_CAPACITY_CHOICES, blank=True, null=True, help_text='RAM capacity e.g. 8GB, 16GB, 32GB, 64GB')
    gpu_vram = models.CharField(max_length=20, choices=GPU_VRAM_CHOICES, blank=True, null=True, help_text='GPU dedicated VRAM e.g. 8GB, 12GB, 16GB, 24GB, 32GB, 64GB, 96GB')
    ssd_capacity = models.CharField(max_length=20, choices=SSD_CAPACITY_CHOICES, blank=True, null=True, help_text='SSD storage capacity e.g. 512GB, 1TB, 2TB, 4TB')
    generation = models.CharField(max_length=20, choices=GENERATION_CHOICES, blank=True, null=True, help_text='Hardware generation e.g. Gen3, Gen4, Gen5')
    cpu_series = models.CharField(max_length=30, choices=CPU_SERIES_CHOICES, blank=True, null=True, help_text='CPU series e.g. Intel Core i3/i5/i7/i9 or AMD Ryzen 3/5/7/9')
    cpu_cores = models.PositiveSmallIntegerField(blank=True, null=True, help_text='CPU physical core count (e.g. 4, 6, 8, 12, 16, 24)')
    cpu_threads = models.PositiveSmallIntegerField(blank=True, null=True, help_text='CPU thread count (e.g. 8, 12, 16, 24, 32)')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand}-{self.name}")
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse('products:product_detail', kwargs={'slug': self.slug})

    @property
    def is_in_stock(self) -> bool:
        return self.stock_qty > 0

    @property
    def discount_percent(self) -> int:
        if self.original_price and self.original_price > self.price:
            return int((self.original_price - self.price) / self.original_price * 100)
        return 0

    @property
    def primary_image_url(self) -> str:
        if self.thumbnail:
            return self.thumbnail.url
        if self.thumbnail_url:
            return self.thumbnail_url
        return 'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=800&auto=format&fit=crop&q=80'

    def __str__(self) -> str:
        return f"{self.brand} {self.name} (${self.price})"

# Model storing gallery images for products
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/4k/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    caption = models.CharField(max_length=150, blank=True)
    is_4k = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    @property
    def display_url(self) -> str:
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return 'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=800&auto=format&fit=crop&q=80'

    def __str__(self) -> str:
        return f"Image for {self.product.name} (#{self.order})"

# Model storing detailed technical specifications table for a product
class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    group = models.CharField(max_length=60, default='Key Specifications')
    spec_name = models.CharField(max_length=100)
    spec_value = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self) -> str:
        return f"{self.product.name} - {self.spec_name}: {self.spec_value}"

# Model storing customer reviews, ratings, and feedback
class ProductReview(models.Model):
    RATING_CHOICES = [
        (5, '5 Stars - Excellent'),
        (4, '4 Stars - Very Good'),
        (3, '3 Stars - Average / Good'),
        (2, '2 Stars - Fair'),
        (1, '1 Star - Poor'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    author_name = models.CharField(max_length=100, help_text='Reviewer name')
    author_email = models.EmailField(blank=True, help_text='Reviewer contact email')
    rating = models.PositiveSmallIntegerField(default=5, choices=RATING_CHOICES)
    title = models.CharField(max_length=150, help_text='Review summary or title')
    comment = models.TextField(help_text='Detailed feedback, benchmark results, or comments')
    is_verified_purchase = models.BooleanField(default=True, help_text='Verified hardware buyer badge')
    is_approved = models.BooleanField(default=True, help_text='Check to display on public product page; uncheck to hide')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product Review'
        verbose_name_plural = 'Product Reviews & Comments'

    def __str__(self) -> str:
        return f"{self.author_name} ({self.rating}★) on {self.product.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalculate average rating and review count from approved reviews
        approved = self.product.reviews.filter(is_approved=True)
        if approved.exists():
            avg_rating = sum(r.rating for r in approved) / approved.count()
            self.product.rating = round(Decimal(str(avg_rating)), 1)
            self.product.review_count = approved.count()
            self.product.save(update_fields=['rating', 'review_count'])
