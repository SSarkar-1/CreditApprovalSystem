from django.core.management.base import BaseCommand
from api.tasks import ingest_customer_data, ingest_loan_data


class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting data ingestion...")
        ingest_customer_data.delay()
        ingest_loan_data.delay()
        self.stdout.write("✅ Ingestion tasks sent to Celery worker!")