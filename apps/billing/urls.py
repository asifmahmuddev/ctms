"""URL routes for paying an order, its invoice, and the cards an account keeps."""

from django.urls import path

from . import views

urlpatterns = [
    path('orders/<int:pk>/pay/', views.PaymentView.as_view(), name='order_pay'),
    path('orders/<int:pk>/invoice/', views.InvoiceView.as_view(), name='invoice'),
    path('orders/<int:pk>/invoice.pdf', views.InvoiceDownloadView.as_view(), name='invoice_download'),
    path('payment-methods/', views.SavedCardListView.as_view(), name='saved_cards'),
    path('payment-methods/<int:pk>/remove/', views.SavedCardDeleteView.as_view(), name='saved_card_delete'),
]
