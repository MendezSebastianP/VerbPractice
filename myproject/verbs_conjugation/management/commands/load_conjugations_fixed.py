import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from verbs.models import Verb
from verbs_conjugation.models import VerbConjugation

class Command(BaseCommand):
    help = 'Loads verb conjugations from CSV file into the database (FIXED VERSION with better duplicate handling)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='conjugations_fixed.csv',
            help='CSV file name (default: conjugations_fixed.csv)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing conjugations before loading new ones',
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            help='Skip duplicate entries instead of updating them',
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
            self.stdout.write('🗑️  Clearing existing conjugations...')
            VerbConjugation.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Existing conjugations cleared.'))

        # Statistics counters
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        self.stdout.write(f'📂 Loading conjugations from: {conjugations_csv_path}')
        self.stdout.write(f'🔧 Skip duplicates mode: {options["skip_duplicates"]}')
        
        # Track duplicates within the CSV file itself
        seen_in_csv = set()
        csv_duplicates = 0
        
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
                        
                        # Create unique identifier for this conjugation
                        unique_key = (verb_id, language, mood, tense, pronoun, conjugated_form)
                        
                        # Check for duplicates within CSV file
                        if unique_key in seen_in_csv:
                            csv_duplicates += 1
                            self.stderr.write(
                                self.style.WARNING(f'Row {row_num}: Duplicate in CSV - {verb.infinitive} ({language}) {mood}/{tense} {pronoun}: {conjugated_form}')
                            )
                            continue
                        
                        seen_in_csv.add(unique_key)
                        
                        # Check if this exact conjugation already exists in the database
                        existing_conjugation = VerbConjugation.objects.filter(
                            verb=verb,
                            language=language,
                            mood=mood,
                            tense=tense,
                            pronoun=pronoun,
                            conjugated_form=conjugated_form
                        ).first()
                        
                        if existing_conjugation:
                            if options['skip_duplicates']:
                                skipped_count += 1
                                continue
                            else:
                                # This is an exact duplicate, no need to update
                                skipped_count += 1
                                continue
                        
                        # Check for conflicting conjugation (same verb/language/mood/tense/pronoun but different form)
                        conflicting_conjugation = VerbConjugation.objects.filter(
                            verb=verb,
                            language=language,
                            mood=mood,
                            tense=tense,
                            pronoun=pronoun
                        ).exclude(conjugated_form=conjugated_form).first()
                        
                        if conflicting_conjugation:
                            # Update the existing conjugation
                            old_form = conflicting_conjugation.conjugated_form
                            conflicting_conjugation.conjugated_form = conjugated_form
                            conflicting_conjugation.save()
                            updated_count += 1
                            
                            self.stdout.write(
                                self.style.WARNING(f'Updated {verb.infinitive} ({language}) {mood}/{tense} {pronoun}: "{old_form}" → "{conjugated_form}"')
                            )
                        else:
                            # Create new conjugation
                            VerbConjugation.objects.create(
                                verb=verb,
                                language=language,
                                mood=mood,
                                tense=tense,
                                pronoun=pronoun,
                                conjugated_form=conjugated_form
                            )
                            created_count += 1
                        
                        # Progress indicator
                        total_processed = created_count + updated_count + skipped_count
                        if total_processed % 1000 == 0:
                            self.stdout.write(f'📊 Processed {total_processed} conjugations...')
                            
                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(f'Row {row_num}: Error processing row: {e}')
                        )
                        error_count += 1
        
        # Final statistics
        total_processed = created_count + updated_count + skipped_count
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎯 CONJUGATION LOADING COMPLETED:\n'
                f'  ✅ Created: {created_count} new conjugations\n'
                f'  🔄 Updated: {updated_count} existing conjugations\n'
                f'  ⏭️  Skipped: {skipped_count} duplicates/unchanged\n'
                f'  ❌ Errors: {error_count} rows with errors\n'
                f'  📊 CSV duplicates found: {csv_duplicates}\n'
                f'  📈 Total processed: {total_processed}\n'
            )
        )
        
        # Show database statistics
        total_in_db = VerbConjugation.objects.count()
        french_in_db = VerbConjugation.objects.filter(language='FR').count()
        spanish_in_db = VerbConjugation.objects.filter(language='ES').count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n📈 DATABASE STATISTICS:\n'
                f'  📚 Total conjugations in database: {total_in_db}\n'
                f'  🇫🇷 French conjugations: {french_in_db}\n'
                f'  🇪🇸 Spanish conjugations: {spanish_in_db}\n'
            )
        )
        
        # Show some sample data
        sample_conjugations = VerbConjugation.objects.select_related('verb')[:5]
        if sample_conjugations:
            self.stdout.write('\n📋 SAMPLE CONJUGATIONS:')
            for conj in sample_conjugations:
                pronoun_part = f"{conj.pronoun} " if conj.pronoun else ""
                self.stdout.write(
                    f'  - {conj.verb.infinitive} ({conj.language}): '
                    f'{conj.mood}/{conj.tense} → {pronoun_part}{conj.conjugated_form}'
                )
        
        # Data quality check
        self.stdout.write(f'\n🔍 QUICK DATA QUALITY CHECK:')
        
        # Check for French tense mixing
        french_present_moods = VerbConjugation.objects.filter(
            language='FR', tense__icontains='présent'
        ).values_list('mood', flat=True).distinct()
        
        if len(french_present_moods) > 1:
            self.stdout.write(f'  ⚠️  Multiple moods in French "présent" tenses: {list(french_present_moods)}')
        else:
            self.stdout.write(f'  ✅ French tense separation looks good')
        
        # Check Spanish pronouns
        spanish_pronouns = set(VerbConjugation.objects.filter(
            language='ES'
        ).values_list('pronoun', flat=True).distinct())
        
        has_standardized_pronouns = 'él/ella' in spanish_pronouns and 'ellos/ellas' in spanish_pronouns
        has_old_pronouns = 'él' in spanish_pronouns and 'ellos' in spanish_pronouns
        
        if has_standardized_pronouns and not has_old_pronouns:
            self.stdout.write(f'  ✅ Spanish pronouns properly standardized')
        elif has_old_pronouns:
            self.stdout.write(f'  ⚠️  Old Spanish pronouns detected: él={VerbConjugation.objects.filter(language="ES", pronoun="él").count()}, ellos={VerbConjugation.objects.filter(language="ES", pronoun="ellos").count()}')
        
        self.stdout.write(f'\n🎉 Loading completed successfully!')
