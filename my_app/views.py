from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth import authenticate, login, logout 
from django.contrib.auth.models import User
from django.db import transaction

from .models import Product, ServiceRental, CartItem, Booking, Order, OrderItem, Payment, CustomerProfile

# --- User Authentication Views ---

def signup_view(request):
    """Handles user registration."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'bikeportal/signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'bikeportal/signup.html')
        
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
            messages.success(request, "Account created successfully! Please log in.")
            return redirect('login')
        except Exception as e:
            messages.error(request, f"Registration failed: {e}")
            return render(request, 'bikeportal/signup.html')
        
    return render(request, 'bikeportal/signup.html')

def login_view(request):
    """Handles user login."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'bikeportal/login.html')

@login_required
def logout_view(request):
    """Handles user logout."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


# --- Page Rendering Views ---

def home_view(request):
    """Renders the Home page."""
    return render(request, 'bikeportal/home.html')

def products_view(request):
    """Renders the Products listing page."""
    products = Product.objects.filter(is_available=True).order_by('category', 'name')
    context = {'products': products}
    return render(request, 'bikeportal/products.html', context)

@login_required
def services_rental_view(request):
    """Renders the Services & Rentals page and user's bookings."""
    services = ServiceRental.objects.all().order_by('service_type', 'name')
    bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')
    booked_ids = bookings.values_list('service_rental_id', flat=True)
    
    context = {
        'services': services,
        'bookings': bookings,
        'booked_ids': booked_ids,
    }
    return render(request, 'bikeportal/services_rental.html', context)

@login_required
def cart_view(request):
    """Renders the Shopping Cart page."""
    cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    total = sum(item.total_price() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_items.aggregate(Sum('quantity'))['quantity__sum'] or 0
    }
    return render(request, 'bikeportal/cart.html', context)

# --- Action Views ---

@login_required
def add_to_cart(request, product_id):
    """Handles adding a product to the user's cart."""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            messages.error(request, "Invalid quantity value.")
            return redirect('products')

        if quantity > 0:
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user, 
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
                messages.success(request, f"Updated {product.name} quantity to {cart_item.quantity}.")
            else:
                messages.success(request, f"Added {product.name} to your cart.")
        
        return redirect('products')
    return redirect('products')

@login_required
def update_cart(request, item_id):
    """Handles updating the quantity of a cart item."""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
        action = request.POST.get('action')
        
        if action == 'increment':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrement':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
        
        return redirect('cart')
    return redirect('cart')

@login_required
def remove_cart(request, item_id):
    """Handles removing a cart item completely."""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
        cart_item.delete()
        messages.success(request, "Item removed from cart.")
        return redirect('cart')
    return redirect('cart')

@login_required
def checkout(request):
    """Processes the payment and creates an actual Order and Payment record."""
    if request.method == 'POST':
        cart_items = CartItem.objects.filter(user=request.user)
        
        if not cart_items.exists():
            messages.error(request, "Your cart is empty!")
            return redirect('cart')
            
        total_amount = sum(item.total_price() for item in cart_items)
        
        # Get user address from profile if available
        user_address = "No address provided"
        try:
            profile = CustomerProfile.objects.get(user=request.user)
            if profile.address:
                user_address = profile.address
        except CustomerProfile.DoesNotExist:
            pass

        # Atomic transaction to ensure order, items, and payment are all created together
        with transaction.atomic():
            # 1. Create the Order
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                shipping_address=user_address,
                status='PROCESSING'
            )

            # 2. Create OrderItems (Snapshots)
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price_at_purchase=item.product.price,
                    quantity=item.quantity
                )

            # 3. Create the Payment record (Initial status: PENDING for KHQR)
            Payment.objects.create(
                order=order,
                payment_method='KHQR',
                amount_paid=total_amount,
                status='PENDING'
            )

            # 4. Clear the User's Cart
            cart_items.delete()
        
        messages.success(request, "Thank you! Your payment is being verified. Your order #{} has been placed.".format(order.id))
        return redirect('home')
        
    return redirect('cart')


@login_required
def book_service(request):
    """Handles the booking of a service or rental."""
    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        preferred_date = request.POST.get('date')
        notes = request.POST.get('notes')
        duration = request.POST.get('duration')
        phone = request.POST.get('phone_number')
        city = request.POST.get('city')
        location = request.POST.get('location')
        
        service = get_object_or_404(ServiceRental, id=service_id)

        Booking.objects.create(
            user=request.user,
            service_rental=service,
            preferred_date=preferred_date,
            notes=notes,
            phone_number=phone, 
            city=city,
            location=location,
            duration_days=duration if service.service_type == 'RENTAL' else None
        )

        messages.success(request, f"Successfully booked {service.name}!")
        return redirect('services_rental')
    
    return redirect('services_rental')

@login_required
def cancel_booking(request, booking_id):
    """Allows a user to cancel their pending booking."""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        booking.delete()
        messages.success(request, "Booking cancelled.")
        return redirect('services_rental')
    return redirect('services_rental')