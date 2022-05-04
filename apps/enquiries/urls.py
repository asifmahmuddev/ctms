"""URL route for the public contact page."""

from django.urls import path

from . import views

urlpatterns = [
    path('contact/', views.ContactEnquiryCreateView.as_view(), name='contact'),
]
