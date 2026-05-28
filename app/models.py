# models.py
from django.db import models
import requests
from django.conf import settings
from decimal import Decimal
import logging
import uuid

class Panier(models.Model):
    user_id = models.IntegerField(
        null=True,
        blank=True
    )
    username = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user_id'], condition=models.Q(user_id__isnull=False), name='unique_cart_per_user'),
        ]


    def __str__(self):
        if self.user_id:
            return f"Cart for {self.user_id}"

class CartItem(models.Model):
    cart = models.ForeignKey('Panier', on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
   

    class Meta:
        unique_together = ('cart', 'product_id')

    def __str__(self):
        return f"{self.quantity} of Product {self.product_id}"
