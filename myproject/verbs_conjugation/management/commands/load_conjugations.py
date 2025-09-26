import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from verbs.models import Verb
from verbs_conjugation.models import VerbConjugation

class Command(BaseCommand):
    help = 'Loads verb conjugations from CSV file into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='conjugations.csv',
            help='CSV file name (default: conjugations.csv)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing conjugations before loading new ones',
        )

    def handle(self, *args, **options):
        # Path to the CSV file
        csv_file = options['file']
        conjugations_csv_path = os.path.join(settings.BASE_DIR, 'verbs_conjugation', 'data', csv_file)
        
        if not os.path.exists(conjugations_csv_path):
            self.stderr.write(
                self.style.ERROR(f'CSV file not found: {conjugations_csv_path}')
            )
            return

        # Clear existing conjugations if requested
        if options['clear']:
            self.stdout.write('Clearing existing conjugations...')
            VerbConjugation.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing conjugations cleared.'))

        # Statistics counters
        created_count = 0
        updated_count = 0
        error_count = 0
        
        self.stdout.write(f'Loading conjugations from: {conjugations_csv_path}')
        
        with open(conjugations_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # Use transaction for better performance
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                    try:
                        # Get the verb object
                        verb_id = int(row['verb_id'])
                        try:
                            verb = Verb.objects.get(id=verb_id)
                        except Verb.DoesNotExist:
                            self.stderr.write(
                                self.style.WARNING(f'Row {row_num}: Verb with ID {verb_id} not found, skipping...')
                            )
                            error_count += 1
                            continue
                        
                        # Extract conjugation data
                        language = row['language'].upper()
                        mood = row['mood']
                        tense = row['tense']
                        pronoun = row['pronoun']
                        conjugated_form = row['conjugated_form']
                        
                        # Validate required fields
                        if not conjugated_form:
                            self.stderr.write(
                                self.style.WARNING(f'Row {row_num}: Empty conjugated_form, skipping...')
                            )
                            error_count += 1
                            continue
                        
                        # Create or update conjugation
                        conjugation, created = VerbConjugation.objects.update_or_create(
                            verb=verb,
                            language=language,
                            mood=mood,
                            tense=tense,
                            pronoun=pronoun,
                            defaults={
                                'conjugated_form': conjugated_form
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                            
                        # Progress indicator
                        if (created_count + updated_count) % 1000 == 0:
                            self.stdout.write(f'Processed {created_count + updated_count} conjugations...')
                            
                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(f'Row {row_num}: Error processing row: {e}')
                        )
                        error_count += 1
        
        # Final statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'\nConjugation loading completed:\n'
                f'  - Created: {created_count} new conjugations\n'
                f'  - Updated: {updated_count} existing conjugations\n'
                f'  - Errors: {error_count} rows with errors\n'
                f'  - Total processed: {created_count + updated_count}\n'
            )
        )
        
        # Show some sample data
        sample_conjugations = VerbConjugation.objects.select_related('verb')[:5]
        if sample_conjugations:
            self.stdout.write('\nSample conjugations loaded:')
            for conj in sample_conjugations:
                pronoun_part = f"{conj.pronoun} " if conj.pronoun else ""
                self.stdout.write(
                    f'  - {conj.verb.infinitive} ({conj.language}): '
                    f'{conj.mood}/{conj.tense} -> {pronoun_part}{conj.conjugated_form}'
                )
