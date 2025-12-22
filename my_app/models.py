import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.forms import ValidationError
from location_field.models.plain import PlainLocationField

# Constants for Service/Rental Type
SERVICE_TYPE_CHOICES = [
    ('RENTAL', 'Services Rental'),
    ('SERVICE', 'Services Maintenance'),
]

PRODUCT_TYPE_CHOICES = [
    ('BICYCLES', 'Bicycles'),
    ('BICYCLE_PARTS', 'Bicycle Parts'),
]

BOOKING_TYPE_CHOICES = [
    ('PENDING', 'Pending'),
    ('ACCEPT', 'Accept'),
]

PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending Verification'),
    ('COMPLETED', 'Payment Completed'),
    ('FAILED', 'Payment Failed'),
]

PAYMENT_METHOD_CHOICES = [
    ('KHQR', 'KHQR (ABA/Wing/ACLEDA)'),
    ('CASH', 'Cash on Delivery'),
]

ORDER_STATUS_CHOICES = [
    ('PROCESSING', 'Processing'),
    ('SHIPPED', 'Shipped'),
    ('DELIVERED', 'Delivered'),
    ('CANCELLED', 'Cancelled'),
]

class CustomerProfile(models.Model):
    """Extends the Django User model to store additional customer-specific data."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

    class Meta:
        verbose_name_plural = "Customer Profiles"

class Product(models.Model):
    """Model for purchasable bikes, gear, and parts."""
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=PRODUCT_TYPE_CHOICES)
    description = models.TextField()
    image = models.ImageField(upload_to='images/')
    quantity = models.PositiveIntegerField(
        default=0,
        help_text="Current stock level available for this product."
    )
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Override save to handle availability based on stock quantity."""
        if self.quantity == 0:
            self.is_available = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        # Orders by newest items first by default
        ordering = ['-created_at']

class ServiceRental(models.Model):
    image = models.ImageField(upload_to='images/')
    name = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='offered_services',
        verbose_name='Service Provider'
    )
    service_type = models.CharField(max_length=10, choices=SERVICE_TYPE_CHOICES)
    price_info = models.CharField(max_length=100)
    duration = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.service_type}) managed by {self.name.username}"
    
    class Meta:
        verbose_name_plural = "Services and Rentals"

class CartItem(models.Model):
    """Model representing an item in a user's shopping cart."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} for {self.user.username}"

class Order(models.Model):
    """Model to store finalized purchase orders."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PROCESSING')
    phone_regex = RegexValidator(regex=r'^\+?855?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True,null=True)
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    """Snapshot of products at the time of purchase."""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order #{self.order.id}"
    
    def save(self, *args, **kwargs):
        """Subtract the ordered quantity from the Product stock upon creation."""
        if not self.pk: # Only on creation
            if self.product:
                # Critical check: Does the store have enough stock?
                if self.product.quantity < self.quantity:
                    raise ValidationError(
                        f"Insufficient stock for {self.product.name}. "
                        f"Only {self.product.quantity} left in stock."
                    )
                
                # Use F() expressions in a real high-traffic app, 
                # but for this logic, we update the instance:
                self.product.quantity -= self.quantity
                self.product.save()
        
        super().save(*args, **kwargs)

    def __str__(self):
        product_name = self.product.name if self.product else "Deleted Product"
        return f"{self.quantity} x {product_name} in Order #{self.order.id}"
    

class Payment(models.Model):
    """Model to handle payment transaction details, specifically for KHQR."""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='KHQR')
    transaction_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4, editable=False, null=True, blank=True) 
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id} - Status: {self.status}"

class Booking(models.Model):
    """Model for services or rentals scheduled by a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service_rental = models.ForeignKey(ServiceRental, on_delete=models.CASCADE)
    preferred_date = models.DateField()
    phone_regex = RegexValidator(regex=r'^\+?855?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    location = PlainLocationField(based_fields=['city'], zoom=7, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='PENDING', choices=BOOKING_TYPE_CHOICES)
    booked_at = models.DateTimeField(auto_now_add=True)
    duration_days = models.IntegerField(blank=True, null=True) 

    def __str__(self):
        return f"Booking of {self.service_rental.name} by {self.user.username} on {self.preferred_date}"