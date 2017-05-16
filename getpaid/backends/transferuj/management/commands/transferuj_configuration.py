from django.core.management.base import BaseCommand
from getpaid.backends.transferuj import PaymentProcessor


class Command(BaseCommand):
    help = 'Display URL path for Transferuj.pl Online URL configuration'

    def handle(self, *args, **options):
        settings_object = PaymentProcessor.get_settings_object()
        key = settings_object.get_configuration_value('key', None)
        if key is None:
            self.stdout.write('Please be sure to provide "key" setting for this backend (random max. 16 characters)')
        else:
            self.stdout.write('Please setup in Transferuj.pl user defined key (for security signing): %s\n' % key)
