"""
Add AVIATOR and WINGO to GameRoom.game_kind choices.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gameroom',
            name='game_kind',
            field=models.CharField(
                choices=[
                    ('SNAKES_LADDERS', 'Snakes & Ladders'),
                    ('LUDO', 'Ludo'),
                    ('CARROM', 'Carrom'),
                    ('AVIATOR', 'Aviator'),
                    ('WINGO', 'Wingo'),
                ],
                max_length=32,
            ),
        ),
    ]
