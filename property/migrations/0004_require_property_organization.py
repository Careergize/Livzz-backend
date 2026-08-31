import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('organizations', '0002_property_scope_and_history'),
        ('property', '0003_property_organization_property_public_id'),
    ]
    operations = [
        migrations.AlterField(
            model_name='property', name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='properties', to='organizations.organization'),
        ),
    ]
