from django.contrib import admin
from .models import CustomerProfile, SellerProfile, Address

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'created_at']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'postal_code', 'street_address', 'is_default']
