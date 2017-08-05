import json
import sys
from datetime import datetime

import django
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.urls import reverse
from django.utils import six
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
import swapper
from getpaid.utils import Site

from getpaid import signals
from django.conf import settings

if six.PY3:
    unicode = str


class BaseOrder(models.Model):
    class Meta:
        abstract = True


class Order(BaseOrder):
    class Meta:
        swappable = swapper.swappable_setting("getpaid", "Order")


PAYMENT_STATUS_CHOICES = (
    ('new', _("new")),
    ('in_progress', _("in progress")),
    ('accepted_for_proc', _("accepted for processing")),
    ('partially_paid', _("partially paid")),
    ('paid', _("paid")),
    ('cancelled', _("cancelled")),
    ('failed', _("failed")),
)


class PaymentManager(models.Manager):
    def get_queryset(self):
        return super(PaymentManager, self).get_queryset().select_related('order')


@python_2_unicode_compatible
class Payment(models.Model):
    """
    This is an abstract class that defines a structure of Payment model that will be
    generated dynamically with one additional field: ``order``
    """

    class Meta:
        ordering = ('-created_on',)
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    objects = PaymentManager()

    amount = models.DecimalField(_("amount"), decimal_places=4, max_digits=20)
    currency = models.CharField(_("currency"), max_length=3)
    status = models.CharField(_("status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default='new', db_index=True)
    backend = models.CharField(_("backend"), max_length=50)
    created_on = models.DateTimeField(_("created on"), auto_now_add=True, db_index=True)
    paid_on = models.DateTimeField(_("paid on"), blank=True, null=True, default=None, db_index=True)
    amount_paid = models.DecimalField(_("amount paid"), decimal_places=4, max_digits=20, default=0)
    external_id = models.CharField(_("external id"), max_length=64, blank=True, null=True)
    description = models.CharField(_("description"), max_length=128, blank=True, null=True)

    order = models.ForeignKey(swapper.get_model_name('getpaid', 'Order'), related_name='payments')
    payment_configuration = models.ForeignKey(swapper.get_model_name('getpaid', 'PaymentConfiguration'))


    def __str__(self):
        return _("Payment #%(id)d") % {'id': self.id}

    # @classmethod
    # def contribute(cls, order, **kwargs):
    #     return {'order': models.ForeignKey(order, **kwargs)}

    @classmethod
    def create(cls, order, backend, request):
        """
            Builds Payment object based on given Order instance
        """
        payment = Payment()
        payment.order = order
        payment.backend = backend
        payment_model = swapper.load_model('getpaid', 'PaymentConfiguration')
        payment_configuration = payment_model.get_settings(backend=backend, request=request)
        payment.payment_configuration = payment_configuration
        signals.new_payment_query.send(sender=None, order=order, payment=payment)
        if payment.currency is None or payment.amount is None:
            raise NotImplementedError('Please provide a listener for getpaid.signals.new_payment_query')
        payment.save()
        signals.new_payment.send(sender=None, order=order, payment=payment)
        return payment

    def get_processor(self):
        try:
            __import__(self.backend)
            module = sys.modules[self.backend]
            return module.PaymentProcessor
        except (ImportError, AttributeError):
            raise ValueError("Backend '%s' is not available or provides no processor." % self.backend)

    def change_status(self, new_status):
        """
        Always change payment status via this method. Otherwise the signal
        will not be emitted.
        """
        if self.status != new_status:
            # do anything only when status is really changed
            old_status = self.status
            self.status = new_status
            self.save()
            signals.payment_status_changed.send(
                    sender=type(self), instance=self,
                    old_status=old_status, new_status=new_status
            )

    def on_success(self, amount=None):
        """
        Called when payment receives successful balance income. It defaults to
        complete payment, but can optionally accept received amount as a parameter
        to handle partial payments.
        Returns boolean value if payment was fully paid
        """
        if getattr(settings, 'USE_TZ', False):
            self.paid_on = datetime.utcnow().replace(tzinfo=utc)
        else:
            self.paid_on = datetime.now()
        if amount:
            self.amount_paid = amount
        else:
            self.amount_paid = self.amount
        fully_paid = (self.amount_paid >= self.amount)
        if fully_paid:
            self.change_status('paid')
        else:
            self.change_status('partially_paid')
        return fully_paid

    def on_failure(self):
        """
        Called when payment was failed
        """
        self.change_status('failed')

    def get_settings_object(self):
        return self.payment_configuration


class PaymentConfigurationBase(models.Model):
    class Meta:
        abstract = True

    backend = models.CharField(max_length=50)
    configuration = models.TextField()

    def get_configuration_value(self, name, default_value=None):
        configuration = json.loads(self.configuration)

        if default_value is not None:
            return configuration.get(name, default_value)
        else:
            try:
                return configuration[name]
            except KeyError:
                raise ImproperlyConfigured("getpaid '%s' requires backend '%s' setting" % (self.backend, name))

    @classmethod
    def get_settings(cls, backend, request):
        return cls.objects.get(backend=backend)

    def get_domain(self, request=None):
        if (hasattr(settings, 'GETPAID_SITE_DOMAIN') and
                settings.GETPAID_SITE_DOMAIN):
            return settings.GETPAID_SITE_DOMAIN
        if django.VERSION[:2] >= (1, 8):
            site = Site.objects.get_current(request=request)
        else:
            site = Site.objects.get_current()

        return site.domain

    def build_absolute_uri(self, view_name, scheme='https', domain=None,
                           reverse_args=None, reverse_kwargs=None):
        if not reverse_args:
            reverse_args = ()
        if not reverse_kwargs:
            reverse_kwargs = {}
        if domain is None:
            domain = self.get_domain()

        path = reverse(view_name, args=reverse_args, kwargs=reverse_kwargs)
        domain = domain.rstrip('/')
        path = path.lstrip('/')

        return u"{0}://{1}/{2}".format(scheme, domain, path)


class PaymentConfiguration(PaymentConfigurationBase):
    class Meta:
        swappable = swapper.swappable_setting("getpaid", "PaymentConfiguration")
