from uuid import uuid4
from django.db import models
from django.db.models import UUIDField
from django.utils import timezone

from account.models import User, QrCode


class Order(models.Model):
    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_code = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    status = models.BooleanField(default=False)


class Transaction(models.Model):
    class TransactionType(models.IntegerChoices):
        MONTHLY_TICKET = 1, 'Monthly Ticket'
        DAILY_TICKET = 2, 'Daily Ticket'
        DEDUCT_TICKET = 3, 'Deduct Ticket'
        REFUND = 4, 'Refund'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    transaction_code = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_user')
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='transaction_order',
        null=True,
        blank=True
    )
    type = models.IntegerField(choices=TransactionType.choices)
    method = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.BooleanField(default=False)


class Ticket(models.Model):
    class TicketType(models.IntegerChoices):
        MONTHLY_TICKET = 1, 'Monthly Ticket'
        DAILY_TICKET = 2, 'Daily Ticket'

    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_user')
    qrcode = models.ForeignKey(QrCode, on_delete=models.CASCADE, related_name='ticket_qrcode')
    price = models.DecimalField(max_digits=10, decimal_places=0)
    expired_at = models.DateTimeField(null=True, blank=True)
    type = models.IntegerField(choices=TicketType.choices)
    created_at = models.DateTimeField(auto_now=True)
