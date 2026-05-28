from django.urls import path
from app.views import EmptyCartView, CartRetrieveView, AddToCartView, RemoveFromCartView
from app import views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('cart/', CartRetrieveView.as_view(), name='carts'),
    path('cart/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/remove/<int:pk>/', RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('cart/<int:product_id>/', views.UpdateItemView.as_view(), name='update-item'),
    path('cart/empty/', EmptyCartView.as_view(), name='empty'),  
    path("health/", views.health),
     
    #Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
