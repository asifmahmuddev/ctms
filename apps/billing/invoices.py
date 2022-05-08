"""Draws an order's invoice as a PDF file.

Measured from the top of the page down, the way an invoice reads, every position a named distance.
"""

import math

from django.conf import settings
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from apps.transport.models import CURRENCY_SYMBOL

from .models import PaymentStatus

PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE

MARGIN = 18 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

# Who the invoice is issued by, printed at the head of every one.
TRADING_NAME = 'CTMS'
FULL_NAME = 'Cargo Transportation Management System'
ADDRESS_LINES = ('11 Commercial Area', 'Dhaka, Bangladesh')
CONTACT_EMAIL = 'asifmahmud.ide@gmail.com'

# The site's own palette, so the invoice and the pages it was drawn from are the same document.
INK = HexColor('#313437')
MUTED = HexColor('#656e76')
BRAND = HexColor('#0b4fd8')
RULE = HexColor('#e3e8ee')
PAID_INK = HexColor('#0d7b48')
REFUNDED_INK = HexColor('#995400')
FAILED_INK = HexColor('#cc2535')

BODY_FONT = 'Helvetica'
BOLD_FONT = 'Helvetica-Bold'

TITLE_SIZE = 20
HEADING_SIZE = 8
BODY_SIZE = 9.5
TOTAL_SIZE = 13

# The mark stands as tall as the wording beside it, so the two read as one lockup.
LOGO_SIZE = 7 * mm
LOGO_GAP = 2.5 * mm

LINE_HEIGHT = 5 * mm
SMALL_LINE_HEIGHT = 4 * mm

# Measured baseline to baseline, so a line above larger wording clears that wording's height.
TITLE_STEP = 8 * mm
NAME_STEP = 6 * mm
NUMBER_STEP = 6.5 * mm
BLOCK_GAP = 9 * mm
HEADING_GAP = 2.5 * mm
RULE_WIDTH = 0.6

# Where each column of the item table starts, measured from the left margin.
COLUMN_OFFSETS = (0, CONTENT_WIDTH * 0.52, CONTENT_WIDTH * 0.70, CONTENT_WIDTH)
COLUMN_HEADINGS = ('Description', 'Weight', 'Distance', 'Amount')

# A note is held to the description column's width, stopping short of the figures to its right.
COLUMN_GUTTER = 4 * mm
DESCRIPTION_WIDTH = COLUMN_OFFSETS[1] - COLUMN_OFFSETS[0] - COLUMN_GUTTER

DATE_FORMAT = '%d %B %Y'

# Written under the item when the desk priced by hand, so the figure is never unexplained.
PRICING_NOTE = 'Priced at {cost} rather than {quoted} · {reason}'

# A reader shows the document's own title, so an invoice names itself rather than "untitled".
DOCUMENT_TITLE = 'Invoice {number}'
DOCUMENT_SUBJECT = 'Invoice for order {reference}'

# The standing, stamped across the foot the way a settled bill is stamped by hand.
STAMP_WIDTH = 54 * mm
STAMP_HEIGHT = 20 * mm
STAMP_ANGLE = 12
STAMP_RADIUS = 2 * mm
STAMP_BORDER = 1.8
STAMP_INNER_BORDER = 0.8
STAMP_INSET = 1.8 * mm
STAMP_PADDING = 2 * mm
STAMP_LABEL_SIZE = 15
STAMP_LABEL_SMALLEST = 9
STAMP_LABEL_STEP = 0.5
STAMP_LABEL_BASELINE = 1.5 * mm
STAMP_DATE_SIZE = 7.5
STAMP_DATE_BASELINE = -6 * mm

# Tilted, the box stands taller and wider than its own sides, and needs the room to match.
STAMP_TILT = math.radians(STAMP_ANGLE)
STAMP_SPAN_WIDTH = STAMP_WIDTH * math.cos(STAMP_TILT) + STAMP_HEIGHT * math.sin(STAMP_TILT)
STAMP_SPAN_HEIGHT = STAMP_WIDTH * math.sin(STAMP_TILT) + STAMP_HEIGHT * math.cos(STAMP_TILT)
STAMP_TEXT_WIDTH = STAMP_WIDTH - 2 * (STAMP_INSET + STAMP_PADDING)

STAMP_COLOURS = {
    PaymentStatus.PENDING: MUTED,
    PaymentStatus.PAID: PAID_INK,
    PaymentStatus.REFUNDED: REFUNDED_INK,
    PaymentStatus.FAILED: FAILED_INK,
}

LOGO_PATH = settings.BASE_DIR / 'static' / 'images' / 'cargo-48px.png'
FILENAME = '{number}.pdf'


class InvoiceCanvas:
    """A page being drawn on, which remembers how far down it has reached."""

    def __init__(self, target):
        self.pdf = canvas.Canvas(target, pagesize=PAGE_SIZE)
        self.y = PAGE_HEIGHT - MARGIN

    def describe(self, title, subject, author):
        """Name the document, which is what a reader puts in its title bar in place of the filename."""

        self.pdf.setTitle(title)
        self.pdf.setSubject(subject)
        self.pdf.setAuthor(author)
        self.pdf.setCreator(author)

    def down(self, distance):
        self.y -= distance

    def text(self, value, offset=0, font=BODY_FONT, size=BODY_SIZE, colour=INK, align='left'):
        """Write one line at the current height, from the left margin plus an offset."""

        self.pdf.setFont(font, size)
        self.pdf.setFillColor(colour)

        x = MARGIN + offset
        if align == 'right':
            self.pdf.drawRightString(x, self.y, str(value))
        else:
            self.pdf.drawString(x, self.y, str(value))

    def line(self, value, step=LINE_HEIGHT, **kwargs):
        """Write one line and step down, by a full line's height unless told otherwise."""

        self.text(value, **kwargs)
        self.down(step)

    def rule(self, width=RULE_WIDTH, colour=RULE):
        self.pdf.setStrokeColor(colour)
        self.pdf.setLineWidth(width)
        self.pdf.line(MARGIN, self.y, PAGE_WIDTH - MARGIN, self.y)


def billing_address(account):
    """Return the lines of an account's address, leaving out the ones it has not filled in."""

    town = ', '.join(part for part in (account.city, account.postal_code) if part)
    return [line for line in (account.get_full_name(), account.email, account.address_line, town, account.country) if line]


def draw_header(page, payment):
    """Draw the mark beside the name, the sender beneath both, and the number against the right edge."""

    top = page.y

    if LOGO_PATH.exists():
        page.pdf.drawImage(str(LOGO_PATH), MARGIN, top - LOGO_SIZE, width=LOGO_SIZE, height=LOGO_SIZE, mask='auto')

    page.y = top - LOGO_SIZE + 1 * mm
    page.line(TRADING_NAME, offset=LOGO_SIZE + LOGO_GAP, font=BOLD_FONT, size=TITLE_SIZE, colour=BRAND, step=NAME_STEP)

    for detail in (FULL_NAME, *ADDRESS_LINES, CONTACT_EMAIL):
        page.line(detail, size=HEADING_SIZE, colour=MUTED, step=SMALL_LINE_HEIGHT)

    left_bottom = page.y

    # The number sits against the right edge, level with the mark, clear of the word heading it.
    page.y = top - LOGO_SIZE + 1 * mm
    page.line('INVOICE', offset=CONTENT_WIDTH, font=BOLD_FONT, size=HEADING_SIZE, colour=MUTED, align='right', step=TITLE_STEP)
    page.line(payment.invoice_number, offset=CONTENT_WIDTH, font=BOLD_FONT, size=TITLE_SIZE, align='right', step=NUMBER_STEP)
    page.y = min(left_bottom, page.y)
    page.down(2 * mm)
    page.rule(width=1.4, colour=INK)
    page.down(BLOCK_GAP)


def draw_parties(page, order, payment):
    """Draw who is billed on the left and the invoice's own facts on the right."""

    top = page.y

    page.line('BILLED TO', font=BOLD_FONT, size=HEADING_SIZE, colour=MUTED)
    for detail in billing_address(order.account):
        page.line(detail)

    left_bottom = page.y
    page.y = top

    facts = (
        ('Issued', payment.paid_at.strftime(DATE_FORMAT)),
        ('Order', order.reference),
        ('Receipt', payment.reference),
        ('Paid by', payment.card_label),
    )
    for label, value in facts:
        page.text(label, offset=CONTENT_WIDTH * 0.55, colour=MUTED)
        page.text(value, offset=CONTENT_WIDTH, align='right')
        page.down(LINE_HEIGHT)

    page.y = min(left_bottom, page.y)
    page.down(BLOCK_GAP)


def wrapped_note(note, width):
    """Break one note to a width, cutting through a word that is too long to stand on a line of its own.

    Splitting on spaces alone lets an unbroken run overhang the column, which an address can carry.
    """

    lines = []

    for line in simpleSplit(note, BODY_FONT, HEADING_SIZE, width):
        while stringWidth(line, BODY_FONT, HEADING_SIZE) > width:
            cut = len(line) - 1
            while cut > 1 and stringWidth(line[:cut], BODY_FONT, HEADING_SIZE) > width:
                cut -= 1

            lines.append(line[:cut])
            line = line[cut:]

        lines.append(line)

    return lines


def item_notes(order):
    """Return the lines written under the item: the route it takes, and why it is priced as it is.

    Both are typed by hand and can run to any length, so each is broken to the description column.
    """

    notes = [f'{order.origin} to {order.destination}']

    if order.has_corrected_cost:
        notes.append(PRICING_NOTE.format(cost=order.cost_label, quoted=order.quoted_cost_label, reason=order.cost_reason))

    return [line for note in notes for line in wrapped_note(note, DESCRIPTION_WIDTH)]


def draw_items(page, order, payment):
    """Draw the one line an order amounts to, and what it totals."""

    for heading, offset in zip(COLUMN_HEADINGS, COLUMN_OFFSETS):
        align = 'right' if heading == COLUMN_HEADINGS[-1] else 'left'
        page.text(heading.upper(), offset=offset, font=BOLD_FONT, size=HEADING_SIZE, colour=MUTED, align=align)

    page.down(HEADING_GAP)
    page.rule()
    page.down(7 * mm)

    page.text(f'{order.get_mode_display()} freight', font=BOLD_FONT)
    page.text(order.weight_label, offset=COLUMN_OFFSETS[1])
    page.text(order.distance_label if order.has_route else 'Not measured', offset=COLUMN_OFFSETS[2])
    page.text(order.cost_label, offset=COLUMN_OFFSETS[3], align='right')
    page.down(LINE_HEIGHT)

    for note in item_notes(order):
        page.line(note, size=HEADING_SIZE, colour=MUTED, step=SMALL_LINE_HEIGHT)

    page.rule()
    page.down(8 * mm)

    page.text('TOTAL', offset=COLUMN_OFFSETS[2], font=BOLD_FONT, size=TOTAL_SIZE)
    total = f'{CURRENCY_SYMBOL}{payment.amount:,}'
    page.text(total, offset=CONTENT_WIDTH, font=BOLD_FONT, size=TOTAL_SIZE, align='right')
    page.down(BLOCK_GAP)


def stamped_label_size(pdf, label):
    """Return the largest size at which a standing still fits between the stamp's rings."""

    size = STAMP_LABEL_SIZE
    while size > STAMP_LABEL_SMALLEST and pdf.stringWidth(label, BOLD_FONT, size) > STAMP_TEXT_WIDTH:
        size -= STAMP_LABEL_STEP

    return size


def draw_stamp(page, payment):
    """Stamp the standing across the foot, tilted, in the colour that standing wears everywhere else."""

    colour = STAMP_COLOURS[PaymentStatus(payment.status)]
    label = payment.get_status_display().upper()
    moment = payment.paid_at if payment.is_settled else payment.updated_at

    pdf = page.pdf
    pdf.saveState()
    pdf.translate(MARGIN + STAMP_SPAN_WIDTH / 2, page.y - STAMP_SPAN_HEIGHT / 2)
    pdf.rotate(STAMP_ANGLE)
    pdf.setStrokeColor(colour)
    pdf.setFillColor(colour)

    # Two rings with a gap between them, both measured from the box's own centre outwards.
    pdf.setLineWidth(STAMP_BORDER)
    pdf.roundRect(-STAMP_WIDTH / 2, -STAMP_HEIGHT / 2, STAMP_WIDTH, STAMP_HEIGHT, STAMP_RADIUS)
    pdf.setLineWidth(STAMP_INNER_BORDER)
    pdf.roundRect(
        -STAMP_WIDTH / 2 + STAMP_INSET, -STAMP_HEIGHT / 2 + STAMP_INSET,
        STAMP_WIDTH - 2 * STAMP_INSET, STAMP_HEIGHT - 2 * STAMP_INSET, STAMP_RADIUS
    )

    pdf.setFont(BOLD_FONT, stamped_label_size(pdf, label))
    pdf.drawCentredString(0, STAMP_LABEL_BASELINE, label)
    pdf.setFont(BOLD_FONT, STAMP_DATE_SIZE)
    pdf.drawCentredString(0, STAMP_DATE_BASELINE, moment.strftime(DATE_FORMAT).upper())

    pdf.restoreState()
    page.down(STAMP_SPAN_HEIGHT + BLOCK_GAP)


def draw_footer(page, payment):
    """Draw how the invoice was settled, which is the only note it carries."""

    if payment.is_settled:
        note = f'Paid in full on {payment.paid_at.strftime(DATE_FORMAT)}. Thank you.'
    else:
        standing = payment.get_status_display().lower()
        note = f'This payment is marked {standing} as of {payment.updated_at.strftime(DATE_FORMAT)}.'

    page.line(note, size=HEADING_SIZE, colour=MUTED)


def render_invoice(target, order):
    """Draw the whole invoice for one order onto `target`, which is anything a file can be written to."""

    payment = order.payment_record

    page = InvoiceCanvas(target)
    page.describe(DOCUMENT_TITLE.format(number=payment.invoice_number), DOCUMENT_SUBJECT.format(reference=order.reference), TRADING_NAME)

    draw_header(page, payment)
    draw_parties(page, order, payment)
    draw_items(page, order, payment)
    draw_stamp(page, payment)
    draw_footer(page, payment)

    page.pdf.showPage()
    page.pdf.save()
    return FILENAME.format(number=payment.invoice_number)
