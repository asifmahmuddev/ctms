"""Model for the messages sent through the public contact page."""

from django.db import models

MAX_LENGTH_NAME = 64
MAX_LENGTH_EMAIL = 128
MAX_LENGTH_PHONE = 32
MAX_LENGTH_SUBJECT = 128
MAX_LENGTH_MESSAGE = 1000
MAX_LENGTH_STATUS = 16


class EnquiryStatus(models.TextChoices):
    """Where an enquiry stands, from arriving to being answered or set aside."""

    NEW = 'new', 'New'
    IN_PROGRESS = 'in-progress', 'In progress'
    RESOLVED = 'resolved', 'Resolved'
    CLOSED = 'closed', 'Closed'


class ContactEnquiry(models.Model):
    """One message left on the contact page, by a visitor who need not hold an account."""

    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=MAX_LENGTH_STATUS, choices=EnquiryStatus.choices, default=EnquiryStatus.NEW)

    name = models.CharField(max_length=MAX_LENGTH_NAME)
    email = models.EmailField(max_length=MAX_LENGTH_EMAIL)
    phone = models.CharField(max_length=MAX_LENGTH_PHONE, blank=True, null=True)
    subject = models.CharField(max_length=MAX_LENGTH_SUBJECT)
    message = models.TextField(max_length=MAX_LENGTH_MESSAGE)

    class Meta:
        verbose_name_plural = 'contact enquiries'
        ordering = ('-submitted_at',)

    def __str__(self):
        return f'{self.subject} from {self.name}'
