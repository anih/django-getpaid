from getpaid.abstract_mixin import AbstractMixin
from getpaid.backends.paypal.helpers import duplicate_txn_id, check_secret
from getpaid.backends.paypal import paypalTransactionStatus as pts
from django.db import models
from django.conf import settings
import urllib2
import logging
logger = logging.getLogger('getpaid.backends.paypal')

class PaymentPaypalFactory(models.Model, AbstractMixin):
    format = u"<IPN: %s %s>"
    PAYMENT_STATUS_CHOICES = (pts.ST_PP_ACTIVE, pts.ST_PP_CANCELLED, pts.ST_PP_CLEARED, pts.ST_PP_COMPLETED,
                              pts.ST_PP_DENIED, pts.ST_PP_PAID, pts.ST_PP_PENDING, pts.ST_PP_PROCESSED,
                              pts.ST_PP_REFUSED, pts.ST_PP_REVERSED, pts.ST_PP_REWARDED, pts.ST_PP_UNCLAIMED,
                              pts.ST_PP_UNCLEARED)

    # Transaction and Notification-Related Variables
    business = models.CharField(max_length=127, blank=True, help_text="Email where the money was sent.")
    charset=models.CharField(max_length=32, blank=True)
    custom = models.CharField(max_length=255, blank=True)
    notify_version = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    parent_txn_id = models.CharField("Parent Transaction ID", max_length=19, blank=True)
    receiver_email = models.EmailField(max_length=127, blank=True)
    receiver_id = models.CharField(max_length=127, blank=True)  # 258DLEHY2BDK6
    residence_country = models.CharField(max_length=2, blank=True)
    test_ipn = models.BooleanField(default=False, blank=True)
    txn_id = models.CharField("Transaction ID", max_length=19, blank=True, help_text="PayPal transaction ID.", db_index=True)
    txn_type = models.CharField("Transaction Type", max_length=128, blank=True, help_text="PayPal transaction type.")
    verify_sign = models.CharField(max_length=255, blank=True)

    # Buyer Information Variables
    address_country = models.CharField(max_length=64, blank=True)
    address_city = models.CharField(max_length=40, blank=True)
    address_country_code = models.CharField(max_length=64, blank=True, help_text="ISO 3166")
    address_name = models.CharField(max_length=128, blank=True)
    address_state = models.CharField(max_length=40, blank=True)
    address_status = models.CharField(max_length=11, blank=True)
    address_street = models.CharField(max_length=200, blank=True)
    address_zip = models.CharField(max_length=20, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=64, blank=True)
    last_name = models.CharField(max_length=64, blank=True)
    payer_business_name = models.CharField(max_length=127, blank=True)
    payer_email = models.CharField(max_length=127, blank=True)
    payer_id = models.CharField(max_length=13, blank=True)

    # Non-PayPal Variables - full IPN/PDT query and time fields.
    flag = models.BooleanField(default=False, blank=True)
    flag_code = models.CharField(max_length=16, blank=True)
    flag_info = models.TextField(blank=True)
    query = models.TextField(blank=True)  # What we sent to PayPal.
    response = models.TextField(blank=True)  # What we got back.

    # Payment Information Variables
    auth_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    auth_exp = models.CharField(max_length=28, blank=True)
    auth_id = models.CharField(max_length=19, blank=True)
    auth_status = models.CharField(max_length=9, blank=True)
    exchange_rate = models.DecimalField(max_digits=64, decimal_places=16, default=0, blank=True, null=True)
    invoice = models.CharField(max_length=127, blank=True)
    item_name = models.CharField(max_length=127, blank=True)
    item_number = models.CharField(max_length=127, blank=True)
    mc_currency = models.CharField(max_length=32, default="USD", blank=True)
    mc_fee = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_gross = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_handling = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_shipping = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    memo = models.CharField(max_length=255, blank=True)
    num_cart_items = models.IntegerField(blank=True, default=0, null=True)
    option_name1 = models.CharField(max_length=64, blank=True)
    option_name2 = models.CharField(max_length=64, blank=True)
    payer_status = models.CharField(max_length=10, blank=True)
    payment_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    payment_gross = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    payment_status = models.CharField(max_length=9, blank=True)
    payment_type = models.CharField(max_length=7, blank=True)
    pending_reason = models.CharField(max_length=14, blank=True)
    protection_eligibility=models.CharField(max_length=32, blank=True)
    quantity = models.IntegerField(blank=True, default=1, null=True)
    reason_code = models.CharField(max_length=15, blank=True)
    remaining_settle = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    settle_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    settle_currency = models.CharField(max_length=32, blank=True)
    shipping = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    shipping_method = models.CharField(max_length=255, blank=True)
    tax = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    transaction_entity = models.CharField(max_length=7, blank=True)

    # Recurring Payments Variables
    amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    amount_per_cycle = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    initial_payment_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    next_payment_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    outstanding_balance = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    payment_cycle= models.CharField(max_length=32, blank=True) #Monthly
    period_type = models.CharField(max_length=32, blank=True)
    product_name = models.CharField(max_length=128, blank=True)
    product_type= models.CharField(max_length=128, blank=True)
    profile_status = models.CharField(max_length=32, blank=True)
    recurring_payment_id = models.CharField(max_length=128, blank=True)  # I-FA4XVST722B9
    rp_invoice_id= models.CharField(max_length=127, blank=True)  # 1335-7816-2936-1451
    time_created = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")

    # Subscription Variables
    amount1 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    amount2 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    amount3 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_amount1 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_amount2 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_amount3 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    password = models.CharField(max_length=24, blank=True)
    period1 = models.CharField(max_length=32, blank=True)
    period2 = models.CharField(max_length=32, blank=True)
    period3 = models.CharField(max_length=32, blank=True)
    reattempt = models.CharField(max_length=1, blank=True)
    recur_times = models.IntegerField(blank=True, default=0, null=True)
    recurring = models.CharField(max_length=1, blank=True)
    retry_at = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    subscr_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    subscr_effective = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    subscr_id = models.CharField(max_length=19, blank=True)
    username = models.CharField(max_length=64, blank=True)

    # Variables not categorized
    receipt_id= models.CharField(max_length=64, blank=True)  # 1335-7816-2936-1451
    currency_code = models.CharField(max_length=32, default="USD", blank=True)
    handling_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    transaction_subject = models.CharField(max_length=255, blank=True)

    # Where did it come from?
    from_view = models.CharField(max_length=6, null=True, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def contribute(cls, payment):
        return {'payment': models.OneToOneField(payment)}


    def __unicode__(self):
        if self.is_transaction():
            return self.format % ("Transaction", self.txn_id)
        else:
            return self.format % ("Recurring", self.recurring_payment_id)

    def is_transaction(self):
        return len(self.txn_id) > 0

    def is_recurring(self):
        return len(self.recurring_payment_id) > 0

    def is_subscription_cancellation(self):
        return self.txn_type == "subscr_cancel"

    def is_subscription_end_of_term(self):
        return self.txn_type == "subscr_eot"

    def is_subscription_modified(self):
        return self.txn_type == "subscr_modify"

    def is_subscription_signup(self):
        return self.txn_type == "subscr_signup"

    def is_recurring_create(self):
        return self.txn_type == "recurring_payment_profile_created"

    def is_recurring_payment(self):
        return self.txn_type == "recurring_payment"

    def is_recurring_cancel(self):
        return self.txn_type == "recurring_payment_profile_cancel"

    def set_flag(self, info, code=None):
        """Sets a flag on the transaction and also sets a reason."""
        self.flag = True
        self.flag_info += info
        if code is not None:
            self.flag_code = code

    def verify(self, item_check_callable=None, receiver_email=None):
        """
        Verifies an IPN and a PDT.
        Checks for obvious signs of weirdness in the payment and flags appropriately.

        Provide a callable that takes an instance of this class as a parameter and returns
        a tuple (False, None) if the item is valid. Should return (True, "reason") if the
        item isn't valid. Strange but backward compatible :) This function should check
        that `mc_gross`, `mc_currency` `item_name` and `item_number` are all correct.

        """
        self.response = self._postback()
        self._verify_postback()
        if not self.flag:
            if self.is_transaction():
                if self.payment_status not in self.PAYMENT_STATUS_CHOICES:
                    self.set_flag("Invalid payment_status. (%s)" % self.payment_status)
                if duplicate_txn_id(self):
                    self.set_flag("Duplicate txn_id. (%s)" % self.txn_id)
                if self.receiver_email != receiver_email:
                    self.set_flag("Invalid receiver_email. (%s)" % self.receiver_email)
                if callable(item_check_callable):
                    flag, reason = item_check_callable(self)
                    if flag:
                        self.set_flag(reason)
            else:
                # @@@ Run a different series of checks on recurring payments.
                pass

        self.save()
        #self.send_signals()

    def verify_secret(self, form_instance, secret):
        """Verifies an IPN payment over SSL using EWP."""
        if not check_secret(form_instance, secret):
            self.set_flag("Invalid secret. (%s)") % secret
        self.save()
        #self.send_signals()


    def get_endpoint(self):
        """Set Sandbox endpoint if the test variable is present."""
        # backends_settings = getattr(settings, 'GETPAID_BACKENDS_SETTINGS', {})
        # backends_settings = backends_settings.get('paypal', {})
        # if self.test_ipn:
        #     return backends_settings.get('SANDBOX_POSTBACK_ENDPOINT')
        # else:
        #     return backends_settings.get('POSTBACK_ENDPOINT')
        from getpaid.backends.paypal import PaymentProcessor
        return '%s' % PaymentProcessor._get_gateway_url

    def initialize(self, request):
        """Store the data we'll need to make the postback from the request object."""
        self.query = getattr(request, request.method).urlencode()
        self.payment_id = self.custom

    def _postback(self):
        """Perform PayPal Postback validation."""
        logger.debug('seinding postback to %s%s' %(self.get_endpoint(), "cmd=_notify-validate&%s" % self.query))
        return urllib2.urlopen(self.get_endpoint(), "cmd=_notify-validate&%s" % self.query).read()

    def _verify_postback(self):
        if self.response != "VERIFIED":
            self.set_flag("Invalid postback. (%s)" % self.response)

    # def send_signals(self):
    #     """Shout for the world to hear whether a txn was successful."""
    #     # Transaction signals:
    #     if self.is_transaction():
    #         if self.flag:
    #             payment_was_flagged.send(sender=self)
    #         else:
    #             payment_was_successful.send(sender=self)
    #     # Recurring payment signals:
    #     # XXX: Should these be merged with subscriptions?
    #     elif self.is_recurring():
    #         if self.is_recurring_create():
    #             recurring_create.send(sender=self)
    #         elif self.is_recurring_payment():
    #             recurring_payment.send(sender=self)
    #         elif self.is_recurring_cancel():
    #             recurring_cancel.send(sender=self)
    #     # Subscription signals:
    #     else:
    #         if self.is_subscription_cancellation():
    #             subscription_cancel.send(sender=self)
    #         elif self.is_subscription_signup():
    #             subscription_signup.send(sender=self)
    #         elif self.is_subscription_end_of_term():
    #             subscription_eot.send(sender=self)
    #         elif self.is_subscription_modified():
    #             subscription_modify.send(sender=self)

PaymentPaypal = None

def build_models(payment_class):
    global PaymentPaypal
    class PaymentPaypal(PaymentPaypalFactory.construct(payment_class)):
        pass
    return [PaymentPaypal]