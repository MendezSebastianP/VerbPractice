import csv
import os
from django.core.management.base import BaseCommand
from verbs.models import Verb

class Command(BaseCommand):
    help = 'Load verbs from CSV file into the database'

    def handle(self, *args, **options):
        # Get the path to the CSV file
        csv_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', '1000verbs.csv')
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found at {csv_file_path}'))
            return
        
        # Clear existing verbs
        Verb.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared existing verbs'))
        
        # Load verbs from CSV
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            verbs_created = 0
            
            for row in reader:
                try:
                    infinitive = row['FR'].strip()
                    translation = row['ES'].strip()
                    
                    if infinitive and translation:
                        verb, created = Verb.objects.get_or_create(
                            infinitive=infinitive,
                            defaults={'translation': translation}
                        )
                        if created:
                            verbs_created += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error processing row {row}: {e}'))
                    continue
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {verbs_created} verbs into the database')
        )
