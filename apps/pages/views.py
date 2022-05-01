"""Views for the public information pages."""

from django.shortcuts import render

INDEX_TEMPLATE = 'pages/index.html'
ABOUT_TEMPLATE = 'pages/about.html'


def index(request):
    return render(request, INDEX_TEMPLATE)


def about(request):
    return render(request, ABOUT_TEMPLATE)
