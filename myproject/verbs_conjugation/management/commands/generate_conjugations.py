import csv
import mlconjug3
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime

class Command(BaseCommand):
    help = 'Generates a CSV file with conjugations for French and Spanish verbs.'

    def handle(self, *args, **options):
        # Path to the source CSV file with verbs
        verbs_csv_path = os.path.join(settings.BASE_DIR, 'verbs', 'data', '1000verbs.csv')
        
        # Path for the output CSV file
        output_dir = os.path.join(settings.BASE_DIR, 'verbs_conjugation', 'data')
        os.makedirs(output_dir, exist_ok=True)
        conjugations_csv_path = os.path.join(output_dir, 'conjugations.csv')
        
        # Path for the error log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_log_path = os.path.join(output_dir, f'conjugation_errors_{timestamp}.txt')

        # Initialize conjugators
        fr_conjugator = mlconjug3.Conjugator(language='fr')
        es_conjugator = mlconjug3.Conjugator(language='es')

        verbs_to_conjugate = []
        with open(verbs_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                verbs_to_conjugate.append({
                    'id': row['ID'],
                    'fr': row['FR'].strip(),
                    'es': row['ES'].strip().split(',')[0] # Take the first Spanish verb if multiple
                })

        with open(conjugations_csv_path, 'w', newline='', encoding='utf-8') as f, \
             open(error_log_path, 'w', encoding='utf-8') as error_log:
            
            writer = csv.writer(f)
            writer.writerow(['verb_id', 'language', 'mood', 'tense', 'pronoun', 'conjugated_form'])
            
            # Write header to error log
            error_log.write(f"Conjugation Errors Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            error_log.write("=" * 60 + "\n\n")

            for verb_data in verbs_to_conjugate:
                self.stdout.write(f"Processing verb ID: {verb_data['id']}")

                # French conjugations
                if verb_data['fr']:
                    try:
                        fr_verb = fr_conjugator.conjugate(verb_data['fr'])
                        if fr_verb:
                            for conjugation_tuple in fr_verb.iterate():
                                if len(conjugation_tuple) == 4:  # (mood, tense, pronoun, conjugated_form)
                                    mood, tense, pronoun, conjugated = conjugation_tuple
                                    if conjugated:  # Skip None values
                                        writer.writerow([verb_data['id'], 'FR', mood, tense, pronoun, conjugated])
                                elif len(conjugation_tuple) == 3:  # (mood, tense, infinitive_form)
                                    mood, tense, conjugated = conjugation_tuple
                                    if conjugated:  # Skip None values
                                        writer.writerow([verb_data['id'], 'FR', mood, tense, '', conjugated])
                        else:
                            error_msg = f"Verb ID {verb_data['id']}: French verb '{verb_data['fr']}' returned no conjugations\n"
                            error_log.write(error_msg)
                            self.stderr.write(self.style.WARNING(error_msg.strip()))
                    except Exception as e:
                        error_msg = f"Verb ID {verb_data['id']}: Could not conjugate French verb '{verb_data['fr']}': {e}\n"
                        error_log.write(error_msg)
                        self.stderr.write(self.style.ERROR(error_msg.strip()))

                # Spanish conjugations
                if verb_data['es']:
                    try:
                        es_verb = es_conjugator.conjugate(verb_data['es'])
                        if es_verb:
                            for conjugation_tuple in es_verb.iterate():
                                if len(conjugation_tuple) == 4:  # (mood, tense, pronoun, conjugated_form)
                                    mood, tense, pronoun, conjugated = conjugation_tuple
                                    if conjugated:  # Skip None values
                                        writer.writerow([verb_data['id'], 'ES', mood, tense, pronoun, conjugated])
                                elif len(conjugation_tuple) == 3:  # (mood, tense, infinitive_form)
                                    mood, tense, conjugated = conjugation_tuple
                                    if conjugated:  # Skip None values
                                        writer.writerow([verb_data['id'], 'ES', mood, tense, '', conjugated])
                        else:
                            error_msg = f"Verb ID {verb_data['id']}: Spanish verb '{verb_data['es']}' returned no conjugations\n"
                            error_log.write(error_msg)
                            self.stderr.write(self.style.WARNING(error_msg.strip()))
                    except Exception as e:
                        error_msg = f"Verb ID {verb_data['id']}: Could not conjugate Spanish verb '{verb_data['es']}': {e}\n"
                        error_log.write(error_msg)
                        self.stderr.write(self.style.ERROR(error_msg.strip()))

        self.stdout.write(self.style.SUCCESS(f'Successfully generated conjugations file at {conjugations_csv_path}'))
        self.stdout.write(self.style.SUCCESS(f'Error log saved at {error_log_path}'))
