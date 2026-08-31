import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def create_initial_history(apps, schema_editor):
    Property = apps.get_model('property', 'Property')
    History = apps.get_model('organizations', 'PropertyOrganizationHistory')
    for prop in Property.objects.exclude(organization_id=None).iterator():
        History.objects.get_or_create(
            property_id=prop.pk, organization_id=prop.organization_id, ended_at=None,
            defaults={'started_at': prop.created_at or timezone.now(), 'note': 'Initial legacy ownership backfill'},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('organizations', '0001_initial'),
        ('property', '0003_property_organization_property_public_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='PropertyAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('membership', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='property_accesses', to='organizations.organizationmembership')),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_grants', to='property.property')),
            ],
        ),
        migrations.CreateModel(
            name='PropertyOrganizationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField()),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('note', models.CharField(blank=True, max_length=500)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='property_history', to='organizations.organization')),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='organization_history', to='property.property')),
            ],
        ),
        migrations.AddConstraint(
            model_name='propertyaccess',
            constraint=models.UniqueConstraint(fields=('membership', 'property'), name='unique_membership_property_access'),
        ),
        migrations.RunPython(create_initial_history, migrations.RunPython.noop),
    ]
