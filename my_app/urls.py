from django.urls import path
from . import views

urlpatterns = [
    # Main Navigation Paths
    path('', views.home_view, name='home'),
    path('products/', views.products_view, name='products'),
    path('services-rental/', views.services_rental_view, name='services_rental'),
    path('cart/', views.cart_view, name='cart'),
    
    # User Authentication Paths (NEW)
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Action Paths (POST requests)
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('remove-cart/<int:item_id>/', views.remove_cart, name='remove_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('book-service/', views.book_service, name='book_service'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
]