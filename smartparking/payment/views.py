from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from payos import PayOS
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, redirect
import random
from payos import PaymentData, ItemData

from account.models import QrCode
from .models import Transaction, Ticket, Order
from account.views import redirect_if_authenticated

import logging

logger = logging.getLogger(__name__)

try:
    payOS = PayOS(
        client_id=settings.PAYOS_CLIENT_ID,
        api_key=settings.PAYOS_API_KEY,
        checksum_key=settings.PAYOS_CHECKSUM_KEY
    )
except Exception as e:
    logger.error(e)


@method_decorator(redirect_if_authenticated, name='dispatch')
class Payment(APIView):
    def post(self, request):
        try:
            data = request.data
            data = payOS.verifyPaymentWebhookData(data)

            if data.description in ['Ma giao dich thu nghiem', "VQRIO123"]:
                return Response({
                        "error": 0,
                        "message": "Ok",
                        "data": None
                    })

            return Response({
                        "error": 0,
                        "message": "Ok",
                        "data": None
                    })
        except Exception as e:
            logger.error(e)
            return Response({
                "error": -1,
                "message": e,
                "data": None
                })


@method_decorator(redirect_if_authenticated, name='dispatch')
class OrderCreate(APIView):
    def post(self, request):
        try:
            body = request.data
            item = ItemData(name=body["productName"], quantity=1, price=body["price"])

            paymentData = PaymentData(
                orderCode=timezone.now().strftime("%Y%m%d%H%M%S%f"), amount=body["price"],
                description=body["description"],
                \
                items=[item], cancelUrl=body["cancelUrl"],
                returnUrl=body["returnUrl"]
            )

            payosCreateResponse = payOS.createPaymentLink(paymentData)
            return Response({
                "error": 0,
                "message": "success",
                "data": payosCreateResponse.to_json()
            })
        except Exception as e:
            logger.error(e)
            return Response({
                "error": -1,
                "message": "Fail",
                "data": None
            })


@method_decorator(redirect_if_authenticated, name='dispatch')
class OrderManage(APIView):
    def get(self, request, pk):
        try:
            data = payOS.getPaymentLinkInfomation(pk)
            return Response(
                {
                    "error": 0,
                    "message": "Ok",
                    "data": data.to_json()
                }
            )
        except Exception as e:
            logger.error(e)
            return Response(
                {
                    "error": -1,
                    "message": "Fail",
                    "data": None
                }
            )

    def put(self, request, pk):
        try:
            order = payOS.cancelPaymentLink(pk)
            return Response(
                {
                    "error": 0,
                    "message": "Ok",
                    "data": order.to_json()
                }
            )
        except Exception as e:
            logger.error(e)
            return Response(
                {
                    "error": -1,
                    "message": "Fail",
                    "data": None
                }
            )


class Webhook(APIView):
    def post(self, request):
        try:
            webhookUrl = request.data["webhook_url"]
            payOS.confirmWebhook(webhookUrl)
            return Response(
                {
                    "error": 0,
                    "message": "Ok",
                    "data": None
                }
            )
        except Exception as e:
            logger.error(e)
            return Response(
                {
                    "error": -1,
                    "message": "Fail",
                    "data": None
                }
            )


def index(request):
    return render(request, "webapp/payment/index.html",)


def success(request):
    return render(request, "webapp/payment/success.html",)


def cancel(request):
    return render(request, "webapp/payment/cancel.html",)


@method_decorator(redirect_if_authenticated, name='dispatch')
class Checkout(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    template_name = 'webapp/payment/index.html'

    def get(self, request):
        try:
            qrcode = QrCode.objects.get(user=request.user)
        except QrCode.DoesNotExist:
            messages.info(request, "Please create qr before buy the ticket!")
            redirect("qrcode")

        query = request.GET.get("query")
        if query is None or query not in ["daily-ticket", "month-ticket"]:
            return HttpResponse(status=404)

        order_type = 2 if query == "daily-ticket" else 1

        description = "Pay the daily ticket invoice" if order_type == 2 \
            else "Pay the month ticket invoice"

        context = {
            "description": description,
            "type": query,
            "months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        }

        return Response(context, template_name=self.template_name, status=200)

    def post(self, request):

        price = request.POST.get("price", "")
        type = request.POST.get("type", "")
        month_quantity = request.POST.get("quantity", "")

        if type not in ["daily-ticket", "month-ticket"]:
            logger.error("missing ticket type")
            messages.error(request, "Missing ticket type !")
            redirect("payment_index", f"?query={type or 'daily-ticket'}")

        if price is None or price < 10000:
            logger.error("missing price")
            messages.error(request, "price must be than 10000 VNĐ")
            redirect("payment_index", f"?query={type or 'daily-ticket'}")

        des_type = "Pay the daily ticket invoice" if type == "daily-ticket" \
            else "Pay the month ticket invoice"

        description = request.POST.get("description", des_type)
        description += f" - {month_quantity} months " if month_quantity != "" else " "

        try:
            item = ItemData(name=description, quantity=1, price=int(price))
            current_site = get_current_site(request)

            paymentData = PaymentData(
                orderCode=int(str(timezone.now().strftime("%H%M%S%f")) + str(random.randint(10, 999))),
                amount=int(price),
                description=description,
                items=[item],
                cancelUrl=f"http://{current_site}/payment/cancel",
                returnUrl=f"http://{current_site}/payment/success"
            )

            payosCreateResponse = payOS.createPaymentLink(paymentData)
            return redirect(payosCreateResponse.checkoutUrl)

        except Exception as e:
            logger.error(e)
            return render(request, "webapp/payment/index.html")