from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.FirebaseLogin.as_view(), name='login'),
    path('logout/', views.account_logout, name='logout'),
    path('register/', views.signup, name='register'),
    path('verify-email/<uid>/<token>/', views.verify_email, name='verify_email'),

    path('profile/', views.profile, name='profile'),
    path('qr-code/', views.get_qrcode, name='qrcode')
]