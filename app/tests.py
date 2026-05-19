from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Panier as Cart
from .models import CartItem
from django.conf import settings
# ~ from django.contrib.auth.models import User
from django.contrib.auth import get_user_model 

User = get_user_model()

class ShoppingCartTests(APITestCase):
    def get_session_key(self):
        session = self.client.session
        if not session.session_key:
            session.save()
        return session.session_key
		
    def authenticate(self, user):
        if user.is_staff:
            token = getattr(settings, "NEW")
        else:
            token = getattr(settings, "NON")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword123'
        )

        self.user2 = User.objects.create_user(
            username='testadmin',
            email='testadmin@example.com',
            password='testpassword123',
            is_staff=True
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
    # --- CartRetrieveView Tests ---
    def test_retrieve_cart(self):
        session_key = self.get_session_key()
        response = self.client.get(f'/cart/?king={session_key}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        # ~ self.assertEqual(response.data['user_id'], 1)

    # --- AddToCartView Tests ---
    def test_add_product_to_cart(self):
        session_key = self.get_session_key()
        data = {'product_id': 1, 'quantity': 2}
        response = self.client.post(f'/cart/add/?king={session_key}', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        cart = Cart.objects.get(session_key=session_key)
        cart_item = CartItem.objects.get(cart=cart, product_id=1)
        self.assertEqual(cart_item.quantity, 2)


    def test_add_nonexistent_product(self):
        session_key = self.get_session_key()
        data = {'product_id': 999, 'quantity': 1}
        response = self.client.post(f'/cart/add/?king={session_key}', data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- RemoveFromCartView Tests ---
    def test_remove_product_from_cart(self):
        session_key = self.get_session_key()
        # Add product to cart first
        self.client.post(f'/cart/add/?king={session_key}', {'product_id': 1, 'quantity': 1})
        response = self.client.delete(f'/cart/remove/1/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        cart = Cart.objects.get(session_key=session_key)
        self.assertFalse(CartItem.objects.filter(cart=cart, product_id=1).exists())

    def test_remove_nonexistent_product_from_cart(self):
        response = self.client.delete('/cart/remove/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_product_not_in_cart(self):
        response = self.client.delete(f'/cart/remove/1/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- EmptyCartView Tests ---
    def test_empty_cart(self):
        session_key = self.get_session_key()
        # Add items to cart
        self.client.post(f'/cart/add/?king={session_key}', {'product_id': 1, 'quantity': 1})
        response = self.client.delete('/cart/empty/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cart.objects.filter(session_key=session_key).exists()) # i dont delete the cart but empty it, maybe should i delete

    def test_empty_nonexistent_cart(self):
        # Ensure no cart exists
        Cart.objects.filter(session_key='').delete()
        response = self.client.delete('/cart/empty/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- UpdateItemView Tests ---
    def test_update_item_quantity(self):
        session_key = self.get_session_key()
        # Add product to cart
        self.client.post(f'/cart/add/?king={session_key}', {'product_id': 1, 'quantity': 1})
        data = {'quantity': 5}
        response = self.client.put(f'/cart/1/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item = CartItem.objects.get(cart=1, product_id=1)
        self.assertEqual(cart_item.quantity, 5)

    def test_update_nonexistent_product(self):
        session_key = self.get_session_key()
        data = {'quantity': 3}
        response = self.client.put('/cart/99/?king={session_key}', data)
        print(self.user.id)
        print('se')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_method_post(self):
        session_key = self.get_session_key()
        data = {'quantity': 2}
        response = self.client.put(f'/cart/?king={session_key}', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # --- Authentication Tests --- 
#    status.HTTP_405
    def test_unauthenticated_access(self):
        session_key = self.get_session_key()
        self.client.logout()
        endpoints = [
            (f'/cart/?king={session_key}', 'get'),
            (f'/cart/add/?king={session_key}', 'post'),
            (f'/cart/1/?king={session_key}', 'put'),
            ('/cart/remove/1/', 'delete'),
            ('/cart/empty/', 'delete'),
        ]
        #status.HTTP_301
        #forbiden is the default, maybe i should overwrite the permission aand the apiview but not autorized is better
        for url, method in endpoints:
            if method == 'get':
                response = self.client.get(url)
            elif method == 'post':
                response = self.client.post(url)
            elif method == 'put':
                response = self.client.put(url)
            elif method == 'delete':
                response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
