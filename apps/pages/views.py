"""Views for the public information pages."""

from django.shortcuts import render

from apps.transport.models import sample_consignment, service_figures

INDEX_TEMPLATE = 'pages/index.html'
ABOUT_TEMPLATE = 'pages/about.html'


def index(request):
    return render(request, INDEX_TEMPLATE, {'consignment': sample_consignment()})


def about(request):
    return render(request, ABOUT_TEMPLATE, {'figures': service_figures()})
