from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_listerprofile'), ('property', '0006_backfill_phase2_assets')]
    operations = [
        migrations.AlterField(
            model_name='property', name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='properties', to=settings.AUTH_USER_MODEL),
        ),
    ]
