"""
.. module:: dj-stripe.contrib.rest_framework.views.

    :synopsis: Views for the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema

from ...models import Customer
from ...settings import CANCELLATION_AT_PERIOD_END, subscriber_request_callback
from .serializers import CreateSubscriptionSerializer, SubscriptionSerializer


class SubscriptionRestView(APIView):
    """API Endpoints for the Subscription object."""

    permission_classes = (IsAuthenticated, )

    @swagger_auto_schema(responses={200: SubscriptionSerializer()})
    def get(self, request, **kwargs):
        """
        Return the customer's valid subscriptions.

        Return the customer's valid subscriptions.
        """
        customer, _created = Customer.get_or_create(subscriber=subscriber_request_callback(self.request), )
        if customer is None or customer.subscription is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = SubscriptionSerializer(customer.subscription)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=CreateSubscriptionSerializer, responses={200: SubscriptionSerializer()})
    def post(self, request, **kwargs):
        """
        Create a new current subscription for the user.

        Create a new current subscription for the user.
        """
        serializer = CreateSubscriptionSerializer(data=request.data)

        if serializer.is_valid():
            try:
                customer, _created = Customer.get_or_create(subscriber=subscriber_request_callback(self.request))
                customer.add_card(serializer.data["stripe_token"])
                charge_immediately = serializer.data.get("charge_immediately")
                if charge_immediately is None:
                    charge_immediately = True

                customer.subscribe(serializer.data["plan"], charge_immediately)
                serializer = SubscriptionSerializer(customer.subscription)

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                # TODO: Better error messages
                return Response("Something went wrong processing the payment: " + str(e),
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={204: ''})
    def delete(self, request, **kwargs):
        """
        Mark the customers current subscription as canceled.

        Mark the customers current subscription as cancelled.
        """
        try:
            customer, _created = Customer.get_or_create(
                subscriber=subscriber_request_callback(self.request)
            )
            customer.subscription.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response("Something went wrong cancelling the subscription.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubscriptionReactivateRestView(APIView):
    """API Endpoints for the Subscription object."""

    permission_classes = (IsAuthenticated, )

    @swagger_auto_schema(responses={204: ''})
    def post(self, request, **kwargs):
        """
        Reactive a current subscription for the user.

        Reactive a current subscription for the user.
        """
        try:
            customer, _created = Customer.get_or_create(subscriber=subscriber_request_callback(self.request))
            customer.subscription.reactivate()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response("Something went wrong reativating the subscription.",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
