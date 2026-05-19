# models.py
from django.db import models
import requests
from django.conf import settings
from decimal import Decimal
import logging
import uuid

class Panier(models.Model):
    session_key = models.CharField(max_length=40, db_index=True, null=True, blank=True)
    cart_token = models.UUIDField(default=uuid.uuid4, unique=True, null=True, blank=True)
    user_id = models.IntegerField(
        null=True,
        blank=True
    )
    username = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # If no user and no session_key, generate a session_key
        if not self.user_id and not self.session_key:
            self.session_key = uuid.uuid4().hex[:40]  # max_length=40 safe
        super().save(*args, **kwargs)
        
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user_id'], condition=models.Q(user_id__isnull=False), name='unique_cart_per_user'),
            models.UniqueConstraint(fields=['session_key'], condition=models.Q(session_key__isnull=False), name='unique_cart_per_session'),
            models.UniqueConstraint(fields=['cart_token'], condition=models.Q(cart_token__isnull=False), name='unique_cart_per_cart'),
        ]


    def __str__(self):
        if self.user_id:
            return f"Cart for {self.user_id}"
        return f"Anonymous cart {self.session_key}"

class CartItem(models.Model):
    cart = models.ForeignKey('Panier', on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
   

    class Meta:
        unique_together = ('cart', 'product_id')

    def __str__(self):
        return f"{self.quantity} of Product {self.product_id}"
