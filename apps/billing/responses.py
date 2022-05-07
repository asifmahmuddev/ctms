"""Turns a drawn invoice into the response that hands it to a browser."""

import io

from django.http import HttpResponse

from .invoices import render_invoice

PDF_CONTENT_TYPE = 'application/pdf'
DOWNLOAD_DISPOSITION = 'attachment; filename="{filename}"'


def invoice_response(order):
    """Return the order's invoice as a PDF the browser downloads rather than displays."""

    buffer = io.BytesIO()
    filename = render_invoice(buffer, order)

    response = HttpResponse(buffer.getvalue(), content_type=PDF_CONTENT_TYPE)
    response['Content-Disposition'] = DOWNLOAD_DISPOSITION.format(filename=filename)
    return response
