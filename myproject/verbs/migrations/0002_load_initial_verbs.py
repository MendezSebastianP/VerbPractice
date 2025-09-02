from django.db import migrations
import csv
from importlib import resources

def load_verbs(apps, schema_editor):
    Verb = apps.get_model('verbs', 'Verb')
    if Verb.objects.exists():
        return
    try:
        with resources.files('verbs').joinpath('data/verbs.csv').open('r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            batch = []
            for row in reader:
                if not row or row[0].startswith('#'):
                    continue
                if len(row) < 2:
                    continue
                inf, tr = row[0].strip(), row[1].strip()
                if inf and tr:
                    batch.append(Verb(infinitive=inf, translation=tr))
            if batch:
                Verb.objects.bulk_create(batch, ignore_conflicts=True)
    except FileNotFoundError:
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('verbs', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(load_verbs, migrations.RunPython.noop),
    ]