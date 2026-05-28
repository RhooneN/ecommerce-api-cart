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
import logging

logger = logging.getLogger(__name__)

def health(request):
    return JsonResponse({"status": "ok"})


class CartRetrieveView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuth]

    def get_object(self):
        try:
            
            panier, _ = Panier.objects.get_or_create(user_id=self.request.user.user_id)
            return panier
            
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Failed to get cart because{e}")
            raise

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Failed to fetch cart  because{e}")
            return Response(
                {"error": "Failed to retrieve cart", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddToCartView(generics.CreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuth]

    def create(self, request, *args, **kwargs):
        
        cart, _ = Panier.objects.get_or_create(user_id=request.user.user_id)
            
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
        print("cart", cart.user_id)
        return Response({"message": "Item added to cart", "updating": f"{resp or None}"}, status=status.HTTP_201_CREATED)




class RemoveFromCartView(generics.DestroyAPIView):
    serializer_class = CartItemDeleteSerializer
    permission_classes = [IsAuth]

    def delete(self, request, *args, **kwargs):
       
           
        try:    
            cart, _ = Panier.objects.get_or_create(user_id=request.user.user_id)
        except Exception as e:
            logger.error(f"Failed to fetch cart because{e}")
            return Response({'error': e}, status=status.HTTP_404_NOT_FOUND)
        
        pk = kwargs.get('pk')
        
        try:
            cart_item = CartItem.objects.get(pk=pk, cart=cart)
            cart_item.delete()
            return Response({"message": "Item removed from cart"}, status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)
       
            
class UpdateItemView(generics.UpdateAPIView):
    serializer_class = CartItemUpdateSerializer
    permission_classes = [IsAuth]
    queryset = CartItem.objects.all()
    lookup_field = 'product_id'
	
    def patch(self, request, id):
        try:
            
            quantity = self.request.data.get('quantity')
            if quantity < 1:
                return Response({"error": "Quantity must be positive"}, status=status.HTTP_400_BAD_REQUEST)
            #The cart will be created and the objet added even when the user neverhad a cart and its his first time selecting the item
            #in this case the update is simply an add. The will of the user is to have this item in his cart at chechout
            cart, _ = Panier.objects.get_or_create(user_id=request.user.user_id) 
           
            item = CartItem.objects.get(cart=cart, product_id=id)
            item.quantity = int(quantity) # is the quantity a safe data sanitized here?
            item.save()
            return Response({"message": "Item quantity patched from cart"}, status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, TypeError):
            logger.error(f"Failed to update item  because{e}")
            return Response({"error": "value error "}, status=status.HTTP_404_NOT_FOUND)
            
class EmptyCartView(generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuth]

    def post(self, request, *args, **kwargs):
           
        try:    
                cart, created = Panier.objects.get_or_create(user_id=request.user.user_id)
                if created:
                     return Response({"message": "Cart emptied successfully "}, status=status.HTTP_204_NO_CONTENT)
                cart.items.all().delete()
                
                return Response({"message": "Cart emptied successfully "}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"error while emptying cart  because{e}")
            return Response({"error": f"{e}"}, status=status.HTTP_404_NOT_FOUND)
        
