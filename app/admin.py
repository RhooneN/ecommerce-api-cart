from django.contrib import admin

# Register your models here.
from .models import Panier 
from .models import CartItem

admin.site.register(Panier)
admin.site.register(CartItem)
