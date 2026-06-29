# Generated manually for adding image field to Lottery model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('lotteries', '0002_lotterytemplate_lottery_auto_draw_lottery_end_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lottery',
            name='image',
            field=models.ImageField(blank=True, help_text='Cover image for the lottery', null=True, upload_to='lotteries/'),
        ),
    ]

