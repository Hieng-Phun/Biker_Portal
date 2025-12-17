from django.db import models
from django.contrib.auth.models import User # Using Django's built-in User model

# Constants for Service/Rental Type
SERVICE_TYPE_CHOICES = [
    ('RENTAL', 'Services Rental'),
    ('SERVICE', 'Services Manternance'),
]

PRODUCT_TYPE_CHOICES = [
    ('BICYCLES', 'Bicycles'),
    ('BICYCLE_PARTS', 'Bicycle Parts'),
]
BOOKING_TYPE_CHOICES = [
    ('PEDING', 'Pending'),
    ('ACCEPT', 'Accept'),
]

class CustomerProfile(models.Model):
    """
    Extends the Django User model (used for SignUp/SignIn) 
    to store additional customer-specific data like phone number and address.
    """
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
    category = models.CharField(max_length=50,choices=PRODUCT_TYPE_CHOICES) # e.g., Road, Mountain, Gear
    description = models.TextField()
    image = models.ImageField(upload_to ='images/')
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.category})"
    
    class Meta:
        verbose_name_plural = "Products"

class ServiceRental(models.Model):
    image = models.ImageField(upload_to ='images/')
    name = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='offered_services',
        verbose_name='Service Provider'
    )
    service_type = models.CharField(max_length=10, choices=SERVICE_TYPE_CHOICES) # RENTAL or SERVICE
    price_info = models.CharField(max_length=100) # e.g., "$45/day" or "$89.99"
    duration = models.CharField(max_length=50) # e.g., "Day", "48 Hrs", "1 Hr"
    description = models.TextField()

    def __str__(self):
        # Updated to use the new field name 'self.user_name.username'
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
        """Calculates the total price for this cart item."""
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} for {self.user.username}"

class Booking(models.Model):
    """Model for services or rentals scheduled by a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service_rental = models.ForeignKey(ServiceRental, on_delete=models.CASCADE)
    preferred_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='PEDING',choices=BOOKING_TYPE_CHOICES)
    booked_at = models.DateTimeField(auto_now_add=True)
    
    # Only applicable for rentals
    duration_days = models.IntegerField(blank=True, null=True) 

    def __str__(self):
        return f"Booking of {self.service_rental.name} by {self.user.username} on {self.preferred_date}"