from django.shortcuts import render
from store.models import Product

def home(request):
    products = Product.objects.filter(is_available=True)[:8]
    context = {
        'products': products
    }
    return render(request, 'home/index.html', context)

def about(request):
    return render(request, 'home/about.html')

def contact(request):
    return render(request, 'home/contact.html')

def feature(request):
    return render(request, 'feature.html')


