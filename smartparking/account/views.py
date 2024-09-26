import hashlib
import qrcode
import json
import requests
from io import BytesIO
from datetime import timedelta
from django.utils import timezone
from PIL import Image
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.core.mail import EmailMessage
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.db import IntegrityError, transaction
from .models import User
from django.http import JsonResponse, HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.response import Response
import firebase_admin
from firebase_admin import credentials, auth
import boto3
from botocore.client import Config

from account.models import QrCode

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import logging

logger = logging.getLogger(__name__)


if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)


def redirect_if_authenticated(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("index")
        return view_func(request, *args, **kwargs)
    return wrapper


def get_s3_resource():
    return boto3.resource(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT if settings.ENVIRONMENT == "dev" else None,
        aws_access_key_id=settings.MINIO_ACCESS_KEY if settings.ENVIRONMENT == "dev" else settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY if settings.ENVIRONMENT == "dev" else settings.AWS_SECRET_KEY,
        region_name=None if settings.ENVIRONMENT == "dev" else settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT_PUBLIC if settings.ENVIRONMENT == "dev" else None,
        aws_access_key_id=settings.MINIO_ACCESS_KEY if settings.ENVIRONMENT == "dev" else settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY if settings.ENVIRONMENT == "dev" else settings.AWS_SECRET_KEY,
        region_name=None if settings.ENVIRONMENT == "dev" else settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )


class FirebaseLogin(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    template_name = 'webapp/accounts/login.html'

    def get(self, request):
        context = {'firebaseConfig': settings.FIREBASE_CONFIG}
        return Response(context, template_name=self.template_name, status=200)

    def post(self, request):
        if request.POST.get("email") and request.POST.get("password"):
            email = request.POST.get("email")
            password = request.POST.get("password")

            user = authenticate(email=email, password=password)
            if user:
                login(request, user)
                return redirect("index")

        id_token = request.data.get('idToken')
        next_url = request.data.get('next', '/')

        if id_token == "":
            return Response({"status": "error", "message": "No idToken provided."}, status=400)

        try:
            decoded_token = auth.verify_id_token(id_token)
            email = decoded_token.get("email")
            login_id = decoded_token.get("sub", "")
            username = decoded_token.get("name", "")
            picture_url = decoded_token.get("picture", "")
            signin_method = decoded_token.get("firebase", {}).get("sign_in_provider", "")

            try:
                user = User.objects.get(login_id=login_id)
                if user.status == "inactive":
                    return Response({"status": "warning", "message": "User account is inactive."}, status=403)

                user.signin_method = signin_method
                user.save()


            except User.DoesNotExist:
                try:
                    with transaction.atomic():
                        extra_fields = {}
                        if picture_url:
                            response = requests.get(picture_url, stream=True)
                            if response.status_code == 200:
                                s3 = get_s3_resource()
                                filename = f"{login_id}.jpg"
                                s3.Bucket(settings.BUCKET_NAME).upload_fileobj(
                                    response.raw,
                                    f"users/{filename}",
                                    ExtraArgs={'ContentType': response.headers['Content-Type']}
                                )
                                extra_fields['picture_key'] = f"users/{filename}"

                        extra_fields['status'] = "active"
                        extra_fields['login_id'] = login_id
                        user = User.objects.create_user(
                            email=email,
                            username=username,
                            password=None,
                            **extra_fields
                        )
                except IntegrityError as e:
                    logger.error(e)
                    return Response(
                        {"status": "error", "message": "User creation failed due to data integrity issues."},
                        status=500)
                except Exception as e:
                    logger.error(e)
                    return Response({"status": "error", "message": f"An error occurred: {str(e)}"}, status=500)

            try:
                login(request, user, backend='account.authentication.FirebaseAuthentication')
            except Exception as e:
                logger.error(e)

            return Response({"status": "success", "next": next_url}, status=200)

        except auth.InvalidIdTokenError as e:
            logger.error(e)
            return Response({"status": "error", "message": "Invalid token."}, status=401)
        except Exception as e:
            logger.error(e)
            return Response({"status": "error", "message": str(e)}, status=500)


def send_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    current_site = get_current_site(request).domain

    verify_url = reverse('verify_email', kwargs={'uid': uid, 'token': token})
    verification_link = f"http://{current_site}{verify_url}"

    mail_subject = "Activate your account"
    parameters = {
        'name': user.username,
        'verification_link': verification_link,
        'app_name': settings.APP_NAME
    }

    mail_body = render_to_string('webapp/accounts/verify.html', parameters)

    mail = EmailMessage(
        subject=mail_subject,
        body=mail_body,
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email]
    )
    mail.content_subtype = "html"

    try:
        user.token = str(token)
        user.save()

        mail.send()
    except Exception as e:
        logger.error(e)
        raise ValueError(f"Error sending email: {e}")


def verify_email(request, uid, token):
    try:
        uid = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=uid)

        if user.token != token:
            messages.error(request, "Token does not match!")
            return redirect("login")

    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        logger.error(e)
        user = None

    if user is not None and default_token_generator.check_token(user, token):

        user.is_active = True
        user.token = None
        user.save()

        messages.success(request, 'Your email has been successfully verified!')
    else:
        messages.success(request, 'The verification link is invalid or has expired!')
    return redirect('account:login')


def signup(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            username = data.get('username')
            id_token = data.get('idToken')

            decoded_token = auth.verify_id_token(id_token)
            login_id = decoded_token.get("sub", "")
            signin_method = decoded_token.get("firebase", {}).get("sign_in_provider", "")

            if email != decoded_token.get("email", ""):
                return JsonResponse({"status": "error", "message": "Email does not match!"}, status=400)

            if User.objects.filter(login_id=login_id).exists():
                return JsonResponse({"status": "error", "message": "User already exists!"}, status=400)
            try:
                with transaction.atomic():
                    extra_fields = {}

                    extra_fields['login_id'] = login_id
                    extra_fields['signin_method'] = signin_method
                    user = User.objects.create_user(
                        email=email,
                        username=username,
                        password=None,
                        **extra_fields
                    )

                    send_email(request, user)

                    messages.success(request, "User created successfully!")

            except Exception as e:
                logger.error(e)
                return JsonResponse({"status": "error", "message": "Cannot create user!"}, status=400)

            return JsonResponse({"status": "success"}, status=200)

        except Exception as e:
            logger.error(e)
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    context = {
        'firebaseConfig': settings.FIREBASE_CONFIG
    }
    return render(request, 'webapp/accounts/register.html', context=context)


@login_required
def account_logout(request):
    logout(request)
    return render(request, 'webapp/home/index.html')


@login_required
def profile(request):
    try:
        account = User.objects.get(email=request.user.email)
        if request.method == "POST":

            username = request.POST.get('username', "")
            phone = request.POST.get('phone', "")
            address = request.POST.get('address', "")
            password = request.POST.get('password', "")

            if request.FILES.get('profile_picture'):
                file = request.FILES.get('profile_picture')
                file_extension = file.name.split('.')[-1].lower()
                filename = f"{account.login_id}.{file_extension}"

                s3 = get_s3_resource()

                s3.Bucket(settings.BUCKET_NAME).upload_fileobj(
                    file,
                    f"users/{filename}",
                    ExtraArgs={'ContentType': request.headers['Content-Type']}
                )
                account.picture_key = f"users/{filename}"

            if username:
                account.username = username
            if phone:
                account.phone_number = phone
            if address:
                account.address = address
            if password:
                account.set_password(password)

            account.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')

    except User.DoesNotExist as e:
        logger.error(e)
        return JsonResponse({"status": "error", "message": "User does not exist!"}, status=404)

    return render(request, 'webapp/accounts/profile.html')


def s3_delete(file_key):
    try:
        s3 = get_s3_client()

        s3.delete_object(Bucket=settings.BUCKET_NAME, Key=file_key)

        return True

    except Exception as e:
        logger.error(e)
        return False


def s3_save_file(file, file_name, file_extension):
    file.seek(0)

    s3 = get_s3_resource()
    s3.Bucket(settings.BUCKET_NAME).upload_fileobj(
        file,
        f"qrcodes/{file_name}.{file_extension}",
        ExtraArgs={'ContentType': "image/png"}
    )
    return f"qrcodes/{file_name}.{file_extension}"


def generate_key_from_password(password):
    hash_func = getattr(hashlib, settings.QRCODE_HASH)
    return hash_func(password.encode()).digest()


def encrypt_data(data, key):
    cipher = AES.new(key, AES.MODE_CBC)
    iv = cipher.iv
    encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return iv + encrypted_data


def qrcode_generate(content):

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=30,
        border=4,
    )

    qr.add_data(content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    buffer = BytesIO()

    img = img.resize((900, 900), Image.Resampling.LANCZOS)

    img.save(buffer, format="PNG")

    file_name = f"qr_code_{get_random_string(8)}"
    file_extension = "png"

    buffer.seek(0)
    s3_path = s3_save_file(buffer, file_name, file_extension)

    return file_name, s3_path


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def get_presigned_url(bucket_name, object_key, expiration=600):

    s3 = get_s3_client()

    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': object_key},
        ExpiresIn=expiration
    )
    return url


@login_required
def get_qrcode(request):
    try:
        user_qrcode = QrCode.objects.get(user=request.user)

        if request.method == "POST" and is_ajax(request):
            otp_key = request.POST.get("otp", "")

            if (timezone.now() - user_qrcode.rendered_at).total_seconds() > 600:
                if not QrCode.verify_otp(user_qrcode, otp_key):
                    return JsonResponse({"status": "error", "message": "OTP verification is invalid!"}, status=400)

            if request.POST.get("type"):
                if request.POST.get("type") == "new_qr":
                    key_password = settings.QRCODE_SECRET_KEY
                    key = generate_key_from_password(key_password)

                    now = timezone.now()

                    key_code = now.strftime("%Y%m%d%H%M%S%f")

                    data = {
                        'key_code': str(key_code),
                        'user_id': str(user_qrcode.user.id)
                    }

                    try:
                        if user_qrcode.key_image:
                            s3 = get_s3_client()
                            s3.delete_object(Bucket=settings.BUCKET_NAME, Key=user_qrcode.key_image)

                        content = str(encrypt_data(str(data), key))
                        file_name, s3_path = qrcode_generate(content)

                        if user_qrcode.key_image:
                            delete_success = s3_delete(user_qrcode.key_image)
                            if not delete_success:
                                return JsonResponse(
                                    {"status": "error", "message": "An error occurred while deleting the old QR code."},
                                    status=400)

                    except Exception as e:
                        logger.error(e)
                        return JsonResponse({"status": "error", "messages": "An error occurred"}, status=400)

                    user_qrcode.key_image = s3_path
                    user_qrcode.key_code = str(key_code)
                    user_qrcode.content = content
                    user_qrcode.updated_at = now
                    user_qrcode.rendered_at = now
                    user_qrcode.save()

                    image_url = get_presigned_url(settings.BUCKET_NAME, s3_path, expiration=600)

                    messages.success(request, "New QR code generated successfully!")

                    return JsonResponse({
                        "status": "success",
                        "image_url": image_url
                    }, status=200)

                elif request.POST.get("type") == "hidden":
                    user_qrcode.rendered_at = timezone.now() - timedelta(minutes=11)
                    user_qrcode.save()
                    return JsonResponse({"status": "success"}, status=200)

                else:
                    return JsonResponse({"status": "error", "message": "Invalid request!"}, status=400)

            else:
                try:
                    image_url = get_presigned_url(settings.BUCKET_NAME, user_qrcode.key_image, expiration=600)
                    user_qrcode.rendered_at = timezone.now()
                    user_qrcode.save()
                except Exception as e:
                    logger.error(e)
                    return JsonResponse({"status": "error", "message": "An error occurred: " + str(e)}, status=400)

                return JsonResponse({"status": "success", "image_url": image_url}, status=200)
        elif request.method == "POST":
            s3 = get_s3_client()

            try:
                response = s3.get_object(Bucket=settings.BUCKET_NAME, Key=user_qrcode.key_image)
                file_content = response['Body'].read()

                response = HttpResponse(file_content, content_type='image/png')
                response['Content-Disposition'] = f'attachment; filename="{user_qrcode.key_code}.png"'

                user_qrcode.rendered_at = timezone.now()
                user_qrcode.save()

                return response

            except Exception as e:
                logger.error(e)
                messages.error(request, f"Could not download the file: {str(e)}")
                redirect('qrcode')

    except QrCode.DoesNotExist:
        if request.method == "POST":

            otp = request.POST.get("otp")
            confirm_otp = request.POST.get("confirm_otp")

            if otp and confirm_otp and otp == confirm_otp and len(otp) == 6 and otp.isdigit():
                try:
                    key_password = settings.QRCODE_SECRET_KEY
                    key = generate_key_from_password(key_password)

                    now = timezone.now()
                    key_code = now.strftime("%Y%m%d%H%M%S%f")

                    data = {
                        'key_code': str(key_code),
                        'user_id': str(request.user.id)
                    }

                    content = str(encrypt_data(str(data), key))
                    file_name, s3_path = qrcode_generate(content)

                    user_qrcode = QrCode.objects.create(
                        user=request.user,
                        key_image=s3_path,
                        key_code=key_code,
                        content=content,
                        password_otp=make_password(otp),
                        created_at=now,
                        updated_at=now,
                        rendered_at=now
                    )

                    image_url = get_presigned_url(settings.BUCKET_NAME, s3_path, expiration=600)

                    messages.success(request, "New QR code generated successfully!")

                    return JsonResponse({
                        "status": "success",
                        "image_url": image_url
                    }, status=200)

                except Exception as e:
                    logger.error(e)
                    return JsonResponse({"status": "error", "message": f"An error occurred: {str(e)}"}, status=400)
            else:
                return JsonResponse({"status": "error", "message": "Invalid OTP!"}, status=400)

    user_qrcode = QrCode.objects.filter(user=request.user).first()

    qrcode_create = False
    context = {"qrcode_create": qrcode_create}

    if user_qrcode:
        qrcode_create = True
        context = {
            "qrcode_create": qrcode_create,
            "qrcode_id": user_qrcode.key_code,
            "created_at": user_qrcode.created_at,
            "modified_at": user_qrcode.updated_at,
            "rendered_at": (timezone.now() - user_qrcode.rendered_at).total_seconds() * 1000
        }

    return render(request, "webapp/accounts/qrcode.html", context=context)
