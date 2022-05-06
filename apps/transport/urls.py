"""URL routes for transport orders."""

from django.urls import path

from . import views

urlpatterns = [
    path('orders/', views.TransportOrderListView.as_view(), name='order_list'),
    path('orders/new/', views.TransportOrderCreateView.as_view(), name='order_create'),
    path('orders/places/', views.place_suggestions, name='place_suggestions'),
    path('orders/<int:pk>/', views.TransportOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/cancel/', views.cancel_order, name='order_cancel'),
]
