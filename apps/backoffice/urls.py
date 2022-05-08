"""URL routes for the back office.

Namespaced, so a name cannot collide with the public side and the navigation knows this section.
"""

from django.urls import path

from . import views

app_name = 'backoffice'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('accounts/', views.AccountListView.as_view(), name='accounts'),
    path('accounts/new/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    path('orders/', views.OrderListView.as_view(), name='orders'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/status/', views.OrderStatusUpdateView.as_view(), name='order_status'),
    path('orders/<int:pk>/cost/', views.OrderCostUpdateView.as_view(), name='order_cost'),
    path('orders/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    path('orders/<int:pk>/payment/', views.PaymentStatusUpdateView.as_view(), name='payment_status'),
    path('orders/<int:pk>/invoice/', views.OrderInvoiceView.as_view(), name='order_invoice'),
    path('orders/<int:pk>/invoice.pdf', views.OrderInvoiceDownloadView.as_view(), name='order_invoice_download'),
    path('payments/', views.PaymentListView.as_view(), name='payments'),
    path('enquiries/', views.EnquiryListView.as_view(), name='enquiries'),
    path('enquiries/<int:pk>/status/', views.EnquiryStatusUpdateView.as_view(), name='enquiry_status'),
    path('enquiries/<int:pk>/delete/', views.EnquiryDeleteView.as_view(), name='enquiry_delete'),
]
