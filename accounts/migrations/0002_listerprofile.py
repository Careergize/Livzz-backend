from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='ListerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lister_type', models.CharField(choices=[('OWNER', 'Owner'), ('BROKER', 'Broker'), ('PROPERTY_MANAGER', 'Property Manager')], max_length=30)),
                ('agency_name', models.CharField(blank=True, max_length=255)),
                ('business_phone', models.CharField(blank=True, max_length=20)),
                ('business_email', models.EmailField(blank=True, max_length=254)),
                ('registration_number', models.CharField(blank=True, max_length=100)),
                ('verification_status', models.CharField(choices=[('UNVERIFIED', 'Unverified'), ('PENDING', 'Pending'), ('VERIFIED', 'Verified'), ('REJECTED', 'Rejected')], default='UNVERIFIED', max_length=20)),
                ('internal_verification_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='lister_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
