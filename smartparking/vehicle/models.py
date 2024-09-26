from django.db import models
from uuid import uuid4
from account.models import User


class Vehicle(models.Model):
    class VehicleTypes(models.TextChoices):
        MOTORCYCLE = 'Motorcycle', 'Motorcycle'
        CAR = 'Car', 'Car'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE,blank=True, null=True, related_name='vehicle_user')
    type = models.CharField(max_length=20, choices=VehicleTypes.choices)
    day_price = models.DecimalField(max_digits=10, decimal_places=2)
    night_price = models.DecimalField(max_digits=10, decimal_places=2)


class ParkingHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parking_history_user')
    check_in = models.DateTimeField(auto_now_add=True)
    check_out = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    license_number = models.CharField(max_length=50)
    image_key = models.CharField(max_length=100)
