from django.contrib import admin
from .models import Category, Product, ProductImage, ProductSpecification, PromotionBanner, ProductReview

admin.site.site_header = 'N-IT Home Management Portal'
admin.site.site_title = 'N-IT Home Admin'
admin.site.index_title = 'Hardware Store Administration & Operations'

# Admin configuration for PromotionBanner
@admin.register(PromotionBanner)
class PromotionBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'card_title', 'card_price', 'is_active', 'order', 'updated_at')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'lead_text', 'card_title')
    fieldsets = (
        ('Banner Status & Ordering', {
            'fields': ('is_active', 'order')
        }),
        ('Main Headline & Text Content', {
            'fields': ('title', 'title_highlight', 'badge_1', 'badge_2', 'lead_text')
        }),
        ('Key Highlight Perks', {
            'fields': ('perk_1', 'perk_2', 'perk_3')
        }),
        ('Featured Promo Card Box (Right Side)', {
            'fields': ('card_tag', 'card_title', 'card_price', 'card_link', 'card_button_text')
        }),
    )

# Inline configuration for ProductReview in Product Admin
class ProductReviewInline(admin.StackedInline):
    model = ProductReview
    extra = 1
    fields = ('author_name', 'author_email', 'rating', 'title', 'comment', 'is_approved', 'is_verified_purchase')

# Inline configuration for ProductImage gallery in Product Admin
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'image_url', 'caption', 'is_4k', 'order')

# Inline configuration for ProductSpecification table in Product Admin
class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 3
    fields = ('group', 'spec_name', 'spec_value', 'order')

# Admin configuration for Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def product_count(self, obj: Category) -> int:
        return obj.products.count()
    product_count.short_description = 'Products'

# Admin configuration for Product
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'brand',
        'category',
        'price',
        'stock_qty',
        'ram_capacity',
        'ram_type',
        'gpu_vram',
        'ssd_capacity',
        'generation',
        'pcie_version',
        'cpu_series',
        'is_featured',
        'updated_at'
    )
    list_filter = (
        'category',
        'brand',
        'generation',
        'ram_type',
        'pcie_version',
        'ram_capacity',
        'gpu_vram',
        'ssd_capacity',
        'cpu_series',
        'is_featured',
        'created_at'
    )
    search_fields = ('name', 'brand', 'short_description', 'ram_capacity', 'ram_type', 'gpu_vram', 'ssd_capacity', 'generation', 'pcie_version', 'cpu_series')
    prepopulated_fields = {'slug': ('brand', 'name')}
    inlines = [ProductImageInline, ProductSpecificationInline, ProductReviewInline]
    list_editable = ('price', 'stock_qty', 'is_featured')
    actions = ['mark_featured', 'unmark_featured', 'set_in_stock']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'brand', 'price', 'original_price', 'stock_qty', 'is_featured', 'warranty')
        }),
        ('Hardware Specifications & Options', {
            'description': 'Admin-controlled hardware spec options used for store search, category filters, and product details.',
            'fields': (
                ('ram_capacity', 'ram_type'),
                ('ssd_capacity', 'generation'),
                ('gpu_vram', 'pcie_version'),
                ('cpu_series', 'cpu_cores', 'cpu_threads'),
            )
        }),
        ('Media & Descriptions', {
            'fields': ('short_description', 'long_description', 'thumbnail', 'thumbnail_url', 'video_url', 'rating', 'review_count')
        }),
    )

    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, 'Selected products marked as Featured.')
    mark_featured.short_description = 'Mark selected products as Featured'

    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, 'Selected products unmarked from Featured.')
    unmark_featured.short_description = 'Unmark selected products from Featured'

    def set_in_stock(self, request, queryset):
        queryset.update(stock_qty=20)
        self.message_user(request, 'Selected products stock set to 20 units.')
    set_in_stock.short_description = 'Set stock to 20 units for selected products'

# Admin configuration for ProductReview
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'author_name', 'rating', 'title', 'is_approved', 'is_verified_purchase', 'created_at')
    list_filter = ('rating', 'is_approved', 'is_verified_purchase', 'created_at', 'product__category')
    search_fields = ('author_name', 'author_email', 'title', 'comment', 'product__name')
    list_editable = ('is_approved',)
    actions = ['approve_reviews', 'unapprove_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, 'Selected reviews have been approved and published.')
    approve_reviews.short_description = 'Approve and publish selected reviews'

    def unapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, 'Selected reviews have been hidden.')
    unapprove_reviews.short_description = 'Hide selected reviews from public view'

# Admin configuration for ProductImage
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'caption', 'is_4k', 'order')
    list_filter = ('is_4k', 'product__category')
    search_fields = ('product__name', 'caption')

# Admin configuration for ProductSpecification
@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('product', 'group', 'spec_name', 'spec_value', 'order')
    list_filter = ('group', 'product__category')
    search_fields = ('product__name', 'spec_name', 'spec_value')
