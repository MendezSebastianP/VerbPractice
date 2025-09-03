from django.db import migrations
import csv
import os

def load_verbs(apps, schema_editor):
    Verb = apps.get_model('verbs', 'Verb')
    if Verb.objects.exists():
        return
    
    # Get the absolute path to the CSV file
    current_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to verbs app directory
    csv_path = os.path.join(current_dir, 'data', '1000verbs.csv')
    
    if not os.path.exists(csv_path):
        print(f"CSV file not found at: {csv_path}")
        return
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                if not row or not row.get('FR') or not row.get('ES'):
                    continue
                inf = row['FR'].strip()
                tr = row['ES'].strip()
                if inf and tr:
                    batch.append(Verb(infinitive=inf, translation=tr))
            if batch:
                Verb.objects.bulk_create(batch, ignore_conflicts=True)
                print(f"Loaded {len(batch)} verbs successfully!")
    except Exception as e:
        print(f"Error loading verbs: {e}")

class Migration(migrations.Migration):
    dependencies = [
        ('verbs', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(load_verbs, migrations.RunPython.noop),
    ]