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

# @login_required
# def cart_view(request):
#     """Renders the Shopping Cart page with location field support."""
#     cart_items = CartItem.objects.filter(user=request.user).select_related('product')
#     total = sum(item.total_price() for item in cart_items)

#     # Try to get default city/address from profile
#     profile_address = ""
#     profile_city = "Phnom Penh"
#     try:
#         profile = CustomerProfile.objects.get(user=request.user)
#         profile_address = profile.address or ""
#     except CustomerProfile.DoesNotExist:
#         pass

#     context = {
#         'cart_items': cart_items,
#         'total': total,
#         'cart_count': cart_items.aggregate(Sum('quantity'))['quantity__sum'] or 0,
#         'profile_address': profile_address,
#         'default_city': profile_city
#     }
#     return render(request, 'bikeportal/cart.html', context)

# @login_required
# def checkout(request):
#     """Processes checkout and captures the Google Map location/address."""
#     if request.method == 'POST':
#         cart_items = CartItem.objects.filter(user=request.user)
        
#         if not cart_items.exists():
#             messages.error(request, "Your cart is empty!")
#             return redirect('cart')
            
#         total_amount = sum(item.total_price() for item in cart_items)
        
#         # Capture precise location and formatted address from the JS Google Maps logic
#         form_city_address = request.POST.get('city') # This contains the formatted address from search
#         form_location = request.POST.get('location') # This contains "lat,lng" string
        
#         # We combine them into the shipping_address field for the order record
#         shipping_info = f"{form_city_address} (GPS: {form_location})"

#         with transaction.atomic():
#             order = Order.objects.create(
#                 user=request.user,
#                 total_amount=total_amount,
#                 shipping_address=shipping_info,
#                 status='PROCESSING'
#             )

#             for item in cart_items:
#                 OrderItem.objects.create(
#                     order=order,
#                     product=item.product,
#                     price_at_purchase=item.product.price,
#                     quantity=item.quantity
#                 )

#             Payment.objects.create(
#                 order=order,
#                 payment_method='KHQR',
#                 amount_paid=total_amount,
#                 status='PENDING'
#             )

#             cart_items.delete()
        
#         messages.success(request, f"Order #{order.id} placed successfully! Delivery location confirmed.")
#         return redirect('home')
        
#     return redirect('cart')

@login_required
def cart_view(request):
    """Renders the Shopping Cart page with location and phone field support."""
    cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    total = sum(item.total_price() for item in cart_items)
    
    # Try to get default data from profile
    profile_address = ""
    profile_phone = ""
    profile_city = "Phnom Penh"
    try:
        profile = CustomerProfile.objects.get(user=request.user)
        profile_address = profile.address or ""
        profile_phone = profile.phone_number or "" # Fetching existing phone number
    except CustomerProfile.DoesNotExist:
        pass

    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_items.aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'profile_address': profile_address,
        'profile_phone': profile_phone,
        'default_city': profile_city
    }
    return render(request, 'bikeportal/cart.html', context)

@login_required
def checkout(request):
    """Processes checkout, validates stock, and captures order details."""
    if request.method == 'POST':
        cart_items = CartItem.objects.filter(user=request.user)
        
        if not cart_items.exists():
            messages.error(request, "Your cart is empty!")
            return redirect('cart')
        
        # 1. Server-side Stock Validation
        # We check all items before starting the transaction to ensure availability
        for item in cart_items:
            if item.quantity > item.product.quantity:
                messages.error(
                    request, 
                    f"Sorry, only {item.product.quantity} units of '{item.product.name}' are left in stock. "
                    f"Please update your cart quantity."
                )
                return redirect('cart')
            
        total_amount = sum(item.total_price() for item in cart_items)
        
        # Capture form data
        form_city_address = request.POST.get('city')
        form_location = request.POST.get('location')
        form_phone = request.POST.get('phone_number')
        
        shipping_info = f"{form_city_address} (GPS: {form_location})"

        try:
            with transaction.atomic():
                # 2. Create the Order
                order = Order.objects.create(
                    user=request.user,
                    total_amount=total_amount,
                    phone_number=form_phone,
                    shipping_address=shipping_info,
                    status='PROCESSING'
                )

                for item in cart_items:
                    product = item.product
                    
                    # 3. Double-check stock inside the atomic transaction (Locking)
                    # We re-fetch the product to ensure we have the latest quantity
                    if product.quantity < item.quantity:
                        raise ValueError(f"Insufficient stock for {product.name}")

                    # 4. Deduct the quantity from the Product model
                    product.quantity -= item.quantity
                    product.save()

                    # Create Order Item
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        price_at_purchase=product.price,
                        quantity=item.quantity
                    )

                # 5. Create Payment record
                Payment.objects.create(
                    order=order,
                    payment_method='KHQR',
                    amount_paid=total_amount,
                    status='PENDING'
                )

                # 6. Clear the user's cart
                cart_items.delete()
            
            messages.success(request, f"Order #{order.id} placed successfully! We will contact you at {form_phone}.")
            return redirect('home')

        except ValueError as e:
            # Handle the error if stock ran out during the processing time
            messages.error(request, str(e))
            return redirect('cart')
        except Exception:
            messages.error(request, "An error occurred while processing your order. Please try again.")
            return redirect('cart')
        
    return redirect('cart')

@login_required
def order_history(request):
    """
    Displays a list of all orders placed by the logged-in user.
    """
    # We use select_related or prefetch_related if you want to optimize 
    # but for a basic history, fetching the orders is sufficient.
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'orders/order_history.html', context)

@login_required
def order_detail(request, order_id):
    """
    Displays the details of a specific order, including all purchased items (OrderItem history).
    """
    # Ensure the user can only view their own orders for security
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Fetch all items associated with this specific order (the order history items)
    # price_at_purchase is used to show what the user actually paid at that time
    order_items = OrderItem.objects.filter(order=order)
    payments = Payment.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': order_items,
        'payments': payments
    }
    return render(request, 'orders/order_detail.html', context)

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