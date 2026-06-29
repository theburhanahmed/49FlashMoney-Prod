from django.db import migrations


def create_default_game(apps, schema_editor):
    SlotsGame = apps.get_model('slots', 'SlotsGame')
    User = apps.get_model('users', 'User')
    admin = User.objects.filter(is_admin=True).first()
    if SlotsGame.objects.filter(name='Lucky Sevens').exists():
        return
    SlotsGame.objects.create(
        name='Lucky Sevens',
        description='Classic 3-reel slots with cherries, lemons, bells, and lucky sevens!',
        is_active=True,
        paytable={
            'seven': 100,
            'bar': 50,
            'bell': 25,
            'plum': 10,
            'orange': 5,
            'lemon': 3,
            'cherry': 2,
        },
        reels=[
            ['cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven', 'seven'],
            ['cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven', 'seven'],
            ['cherry', 'lemon', 'orange', 'plum', 'bell', 'bar', 'seven', 'seven'],
        ],
        rtp_percent=96.00,
        min_bet=0.10,
        max_bet=100.00,
        created_by=admin,
    )


def reverse_create_default_game(apps, schema_editor):
    SlotsGame = apps.get_model('slots', 'SlotsGame')
    SlotsGame.objects.filter(name='Lucky Sevens').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('slots', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_game, reverse_create_default_game),
    ]
