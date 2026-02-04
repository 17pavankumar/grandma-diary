from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Cart, CartItem, Order, OrderItem, Payment
from django.contrib.auth.decorators import login_required
from django.conf import settings
import razorpay
from django.views.decorators.csrf import csrf_exempt

def product_list(request):
    products = Product.objects.filter(is_available=True)
    return render(request, 'products/product_list.html', {'products': products})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    return render(request, 'products/product_detail.html', {'product': product})

def _get_cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
        else:
            cart = Cart.objects.get(session_id=_get_cart_id(request))
    except Cart.DoesNotExist:
        if request.user.is_authenticated:
            cart = Cart.objects.create(user=request.user)
        else:
            cart = Cart.objects.create(session_id=_get_cart_id(request))
    
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        cart_item = CartItem.objects.create(product=product, quantity=1, cart=cart)
        cart_item.save()
    
    return redirect('cart')

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart')

def cart_view(request):
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
        else:
            cart = Cart.objects.get(session_id=_get_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart)
        total = 0
        for item in cart_items:
            total += (item.product.price * item.quantity)
    except Cart.DoesNotExist:
        cart_items = []
        total = 0
    
    return render(request, 'orders/cart.html', {'cart_items': cart_items, 'total': total})

@login_required
def checkout(request):
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
        else:
            # Should not happen due to @login_required but safe fallback
            return redirect('login')
            
        cart_items = CartItem.objects.filter(cart=cart)
        if not cart_items.exists():
            return redirect('product_list')

        total = sum(item.product.price * item.quantity for item in cart_items)
            
        if request.method == 'POST':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            address_text = request.POST.get('address')
            city = request.POST.get('city')
            postcode = request.POST.get('postcode')
            phone = request.POST.get('phone')
            
            # Simple address formation for demo; in real app, save Address model
            full_address = f"{address_text}, {city}, {postcode}"
            
            order = Order.objects.create(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                email=request.user.email,
                address=full_address,
                phone=phone,
                total=total,
                ip=request.META.get('REMOTE_ADDR'),
                paid=False
            )
            
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.price,
                    quantity=item.quantity
                )
            # Do not clear cart yet, wait for payment success
            
            return redirect('payment')
            
    except Cart.DoesNotExist:
        return redirect('product_list')

    return render(request, 'orders/checkout.html', {'cart_items': cart_items, 'total': total})

@login_required
def payment(request):
    try:
        # Get the latest unpaid order
        order = Order.objects.filter(user=request.user, paid=False).order_by('-created_at').first()
        if not order:
            return redirect('product_list')
            
        # Razorpay setup
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_amount = int(order.total * 100) # Amount in paise
        
        razorpay_order = client.order.create({
            'amount': payment_amount,
            'currency': 'INR',
            'payment_capture': '1'
        })
        
        context = {
            'order': order,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_amount': payment_amount,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'currency': 'INR'
        }
        return render(request, 'payments/payment.html', context)
        
    except Exception as e:
        # handle error
        print(e)
        return redirect('checkout')

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('order_id')
        
        # In a real app, verify signature here using razorpay client
        
        if payment_id and order_id:
            try:
                order = Order.objects.get(id=order_id)
                
                # Create Payment record
                payment = Payment.objects.create(
                    user=order.user,
                    payment_id=payment_id,
                    payment_method='Razorpay',
                    amount_paid=str(order.total),
                    status='Paid'
                )
                
                # Update Order
                order.payment = payment
                order.paid = True
                order.save()
                
                # Clear Cart
                try:
                    cart = Cart.objects.get(user=order.user)
                    CartItem.objects.filter(cart=cart).delete()
                except Cart.DoesNotExist:
                    pass
                    
            except Order.DoesNotExist:
                pass
                
    return render(request, 'payments/success.html')
