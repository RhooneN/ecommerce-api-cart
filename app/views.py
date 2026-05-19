from rest_framework import generics, status
from rest_framework.response import Response
from .models import Panier 
from .models import CartItem
from .serializers import CartSerializer, CartItemDeleteSerializer, CartItemSerializer, CartItemUpdateSerializer
from django.shortcuts import get_object_or_404

# When associating cart with user account
from rest_framework.views import APIView
from shared.simple_permissions import IsAuth, IsAuthenticatedOrReadOnly, IsAdmin
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})

class MergeCartView(APIView):
    permission_classes = [IsAuth] 

    def post(self, request, *args, **kwargs):
        user_id = request.user.id 
        cart_token = request.data.get("cart_token")

        if not cart_token:
            return Response({"error": "cart_token required. Start by adding item to cart"}, status=400)

        # 1. Find anonymous cart by token
        anonymous_cart = Panier.objects.filter(cart_token=cart_token, user_id__isnull=True, is_active=True).first()

        # 2. Find or create user cart
        user_cart, _ = Panier.objects.get_or_create(user_id=user_id, is_active=True)

        # 3. Merge items
        if anonymous_cart:
            for item in anonymous_cart.items.all():
                existing = user_cart.items.filter(product_id=item.product_id).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.save()
                else:
                    item.cart = user_cart
                    item.save()
            anonymous_cart.delete()

        return Response({"message": "Carts merged successfully", "cart_id": user_cart.id})



class CartRetrieveView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = []

    def get_object(self):
        try:
            # Anonymous user
            session_key = self.request.query_params.get("king")
            if not session_key:
                # Ensure session exists
                if not self.request.session.session_key:
                    self.request.session.create()
                session_key = self.request.session.session_key
            panier, _ = Panier.objects.get_or_create(	session_key=session_key)
            return panier
            
        except Exception as e:
            # Log the error for debugging
            raise

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {"error": "Failed to retrieve cart", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddToCartView(generics.CreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = []

    def create(self, request, *args, **kwargs):
        session_key = self.request.query_params.get("king")

        if not session_key:
                # Ensure session exists
                if not self.request.session.session_key:
                    self.request.session.create()
                session_key = self.request.session.session_key
                
        cart, _ = Panier.objects.get_or_create(session_key=session_key)
            
        try:
            product_id = int(request.data.get('product_id'))
        except (ValueError, TypeError):
            return Response({"message": f"Please enter a valid product. "}, status=status.HTTP_400_BAD_REQUEST)
        product_data = CartItemSerializer()._get_product_data(product_id)
        if not product_data.get("success", False) or float(product_data.get("price", 0.0)) <= 0:
            error = product_data['error']
            return Response({'message': f"product with id {product_id} not availaible.", "error": f"{error}",  }, status=status.HTTP_404_NOT_FOUND)
        try:
            quantity = int(request.data.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product_id=product_id)
        resp=''
        if not created:
            # ~ return Response({'message': 'Item already in cart. Update quantity instead or choose another to add!'})
            resp = f"You had {cart_item.quantity} and modify it"
        cart_item.quantity = quantity
        cart_item.save()

        return Response({"message": "Item added to cart", "updating": f"{resp or None}"}, status=status.HTTP_201_CREATED)




class RemoveFromCartView(generics.DestroyAPIView):
    serializer_class = CartItemDeleteSerializer
    permission_classes = []

    def delete(self, request, *args, **kwargs):
        
        session_key = self.request.session.session_key
        if  not session_key:
            self.request.session.create()
            return Response({'User dont have a cart actually'}, status=status.HTTP_404_NOT_FOUND)
            # ~ session_key = self.request.session.session_key
        try:    
            cart = Panier.objects.get(session_key=session_key)
        except Panier.DoesNotExist:
            return Response({'User dont have a cart actually'}, status=status.HTTP_404_NOT_FOUND)
        
        pk = kwargs.get('pk')
        
        try:
            cart_item = CartItem.objects.get(pk=pk, cart=cart)
            cart_item.delete()
            return Response({"message": "Item removed from cart"}, status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)
       
            
class UpdateItemView(generics.UpdateAPIView):
    serializer_class = CartItemUpdateSerializer
    permission_classes = []
    queryset = CartItem.objects.all()
    lookup_field = 'product_id'
	
    def patch(self, request, id):
        try:
            session_key = self.request.session.session_key
            if  not session_key:
                self.request.session.create()
                return Response({'User dont have a cart actually'}, status=status.HTTP_404_NOT_FOUND)
            quantity = self.request.data.get('quantity')
            if quantity < 1:
                return Response({"error": "Quantity must be positive"}, status=status.HTTP_400_BAD_REQUEST)
            cart = Panier.objects.get(session_key=session_key)
            item = CartItem.objects.get(cart=cart, product_id=id)
            item.quantity = int(quantity) # is the quantity a safe data sanitized here?
            item.save()
            return Response({"message": "Item quantity patched from cart"}, status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, TypeError):
            return Response({"error": "value error "}, status=status.HTTP_404_NOT_FOUND)
            
class EmptyCartView(generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = []

    def delete(self, request, *args, **kwargs):
        session_key = request.query_params.get("king")
        if not session_key:
            session_key = request.session.session_key
        if  not session_key:
            self.request.session.create()
            return Response({"User doesn' t have a cart actually"}, status=status.HTTP_404_NOT_FOUND)
                
        try:    
                cart = Panier.objects.get(session_key=session_key)
                cart.items.all().delete()
                # ~ for item in cart.items.all():
                     # ~ item.delete()
                return Response({"message": "User cart removed "}, status=status.HTTP_204_NO_CONTENT)
        except Panier.DoesNotExist:
                return Response({"User dont doesn' t have a cart actually"}, status=status.HTTP_404_NOT_FOUND)
        
