"""
Add SCRATCH_CARD to GameRoom.game_kind choices.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_add_aviator_wingo'),
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
                    ('MINES', 'Mines'),
                    ('SCRATCH_CARD', 'Scratch Card'),
                ],
                max_length=32,
            ),
        ),
    ]
