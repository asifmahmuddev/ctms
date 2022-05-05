"""URL routes for the public information pages."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('careers/', views.careers, name='careers'),
]
