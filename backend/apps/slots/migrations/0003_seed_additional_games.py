from django.db import migrations


def create_additional_games(apps, schema_editor):
    SlotsGame = apps.get_model('slots', 'SlotsGame')
    User = apps.get_model('users', 'User')
    admin = User.objects.filter(is_admin=True).first()

    games_to_create = [
        {
            'name': 'Classic Fruits',
            'description': 'Balanced 3-reel fruits slot with medium volatility.',
            'paytable': {
                'seven': 80,
                'bar': 40,
                'bell': 20,
                'plum': 12,
                'orange': 6,
                'lemon': 4,
                'cherry': 2,
            },
            'reels': [
                ['cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven', 'seven'],
                ['cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven', 'seven'],
                ['cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven', 'seven'],
            ],
            'rtp_percent': 96.00,
            'min_bet': 0.10,
            'max_bet': 50.00,
        },
        {
            'name': 'Beginner Low Stakes',
            'description': 'Low-stakes slot with frequent small wins for new players.',
            'paytable': {
                'seven': 40,
                'bar': 25,
                'bell': 15,
                'plum': 8,
                'orange': 5,
                'lemon': 3,
                'cherry': 2,
            },
            'reels': [
                ['cherry', 'cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven'],
                ['cherry', 'cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven'],
                ['cherry', 'cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven'],
            ],
            'rtp_percent': 97.50,
            'min_bet': 0.05,
            'max_bet': 25.00,
        },
    ]

    for cfg in games_to_create:
        if SlotsGame.objects.filter(name=cfg['name']).exists():
            continue
        SlotsGame.objects.create(
            name=cfg['name'],
            description=cfg['description'],
            is_active=True,
            paytable=cfg['paytable'],
            reels=cfg['reels'],
            rtp_percent=cfg['rtp_percent'],
            min_bet=cfg['min_bet'],
            max_bet=cfg['max_bet'],
            created_by=admin,
        )


def reverse_create_additional_games(apps, schema_editor):
    SlotsGame = apps.get_model('slots', 'SlotsGame')
    for name in ['Classic Fruits', 'Beginner Low Stakes']:
        SlotsGame.objects.filter(name=name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('slots', '0002_seed_default_game'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_additional_games, reverse_create_additional_games),
    ]

