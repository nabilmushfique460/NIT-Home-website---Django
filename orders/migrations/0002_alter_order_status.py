from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Placed'), ('CONFIRMED', 'Confirmed'), ('PACKAGING', 'Bench Packaging'), ('SHIPPED', 'In Transit'), ('DELIVERED', 'Delivered'), ('CANCEL_REQUESTED', 'Cancellation Requested'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=20),
        ),
    ]
