from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Product, ServiceRental, CartItem, Booking, CustomerProfile
from django.utils.html import format_html


admin.site.site_header = "Biker Portal"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Biker Portal"

# --- Customer Profile Integration ---
class CustomerProfileInline(admin.StackedInline):
    """Defines the inline display for CustomerProfile within the User admin."""
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    
class CustomUserAdmin(UserAdmin):
    """Custom User Admin model to include the CustomerProfile inline."""
    inlines = (CustomerProfileInline,)

# Unregister the default User admin and register the customized one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
# --- End Customer Profile Integration ---


# Register Product Model
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category','image_preview', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'description')
    readonly_fields = ["image_preview"]
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 80px; height: auto;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

# Register ServiceRental Model
@admin.register(ServiceRental)
class ServiceRentalAdmin(admin.ModelAdmin):
    list_display = ('image_preview','name', 'service_type', 'price_info', 'duration')
    list_filter = ('service_type',)
    search_fields = ('name',)
    readonly_fields = ["image_preview"]
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 80px; height: auto;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'


# Register CartItem Model
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    # Added 'product_image' before 'product' in list_display
    list_display = ('user', 'product_image', 'product', 'quantity', 'total_price', 'added_at')
    list_filter = ('user', 'product__category')
    readonly_fields = ('total_price',)

    def total_price(self, obj):
        """Calculates and returns the total price for the item."""
        # Assuming CartItem model has a total_price() method
        return obj.total_price()
    total_price.short_description = 'Total Price'

    def product_image(self, obj):
        """Displays a small thumbnail of the associated product image."""
        # Check if the product and its image field exist and are not empty
        if obj.product and hasattr(obj.product, 'image') and obj.product.image:
            return format_html(
                '<img src="{}" style="height: 50px; border-radius: 4px; object-fit: cover;" />',
                obj.product.image.url
            )
        return "No Image"

    product_image.short_description = 'Image'
    # Use 'product__image' to allow ordering by the image field (if applicable)
    product_image.admin_order_field = 'product__image'
    # This is handled automatically by format_html, but included for clarity
    product_image.allow_tags = True

# Register Booking Model
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'service_rental', 'preferred_date','phone_number','city','location', 'status', 'booked_at')
    list_filter = ('status', 'service_rental__service_type', 'preferred_date')
    search_fields = ('user__username', 'service_rental__name')
    list_editable = ('status',) # Allow status change directly in the list view