from django.shortcuts import render
from account.models import User
from django.conf import settings


def index(request):
    return render(request, 'webapp/home/index.html')
