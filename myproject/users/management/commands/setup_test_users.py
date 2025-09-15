from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from verbs.services import init_user_verbs
from word_training.services import init_user_words


class Command(BaseCommand):
    help = 'Creates test users for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing test users before creating new ones',
        )

    def handle(self, *args, **options):
        # Test user data
        test_users = [
            {'username': 'admin', 'is_superuser': True, 'is_staff': True},
            {'username': 'testuser1', 'is_superuser': False, 'is_staff': False},
            {'username': 'testuser2', 'is_superuser': False, 'is_staff': False},
        ]
        
        if options['reset']:
            self.stdout.write('Deleting existing test users...')
            User.objects.filter(username__in=[u['username'] for u in test_users]).delete()

        created_count = 0
        for user_data in test_users:
            username = user_data['username']
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'User "{username}" already exists, skipping...')
                continue
            
            # Create user
            if user_data['is_superuser']:
                user = User.objects.create_superuser(
                    username=username,
                    password='Passw1234',
                    email=f'{username}@test.com'
                )
            else:
                user = User.objects.create_user(
                    username=username,
                    password='Passw1234',
                    email=f'{username}@test.com'
                )
            
            # Initialize verbs for this user
            init_user_verbs(user, 10)
            init_user_words(user, 10)
            
            created_count += 1
            user_type = 'superuser' if user_data['is_superuser'] else 'user'
            self.stdout.write(
                self.style.SUCCESS(f'Created {user_type}: {username} (password: Passw1234)')
            )

        if created_count == 0:
            self.stdout.write('No new users created. All test users already exist.')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully created {created_count} test users!')
            )
            self.stdout.write('All users have been initialized with the first 10 verbs.')
            self.stdout.write('\nTest credentials:')
            for user_data in test_users:
                self.stdout.write(f'  {user_data["username"]}: Passw1234')
