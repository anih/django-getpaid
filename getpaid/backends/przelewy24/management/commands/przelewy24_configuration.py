from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from getpaid.backends.przelewy24 import PaymentProcessor
from getpaid.utils import get_domain


class Command(BaseCommand):
    help = 'Additional Przelewy24 configuration'

    def handle(self, *args, **options):
        current_site = get_domain()
        settings_object = PaymentProcessor.get_settings_object()

        self.stdout.write(
            'Please contact with Przelewy24 (serwis@przelewy24.pl) and provide them with the following URL: \n\n')

        self.stdout.write(
            ('https://' if settings_object.get_configuration_value('ssl_return', False) else 'http://') + '%s%s\n\n' % (
                current_site, reverse('getpaid-przelewy24-online'))
        )

        self.stdout.write(
            'This is an additional URL for accepting payment status updates.\n\n')

        self.stdout.write(
            'To change domain name please edit Sites settings. Don\'t forget to setup your web server to accept https connection in order to use secure links.\n')
        if settings_object.get_configuration_value('sandbox', False):
            self.stdout.write('\nSandbox mode is ON.\n')
