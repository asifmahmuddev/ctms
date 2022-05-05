"""Views for the public information pages."""

from django.shortcuts import render

from apps.transport.models import sample_consignment, service_figures

from .content import CAREER_VALUES, SERVICE_PROMISES, freight_services, open_roles

INDEX_TEMPLATE = 'pages/index.html'
ABOUT_TEMPLATE = 'pages/about.html'
SERVICES_TEMPLATE = 'pages/services.html'
CAREERS_TEMPLATE = 'pages/careers.html'


def index(request):
    return render(request, INDEX_TEMPLATE, {'consignment': sample_consignment()})


def about(request):
    return render(request, ABOUT_TEMPLATE, {'figures': service_figures()})


def services(request):
    return render(request, SERVICES_TEMPLATE, {'services': freight_services(), 'promises': SERVICE_PROMISES})


def careers(request):
    return render(request, CAREERS_TEMPLATE, {'values': CAREER_VALUES, 'roles': open_roles()})
