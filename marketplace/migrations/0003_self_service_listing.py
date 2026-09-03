from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_listerprofile'), ('property', '0007_nullable_legacy_property_owner'),
                    ('marketplace', '0002_conservative_legacy_marketplace')]
    operations = [
        migrations.AddField(model_name='listing', name='lister_profile', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='listings', to='accounts.listerprofile')),
        migrations.CreateModel(name='ListingDraft', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ('current_step', models.CharField(choices=[('PROPERTY_TYPE','Property Type'),('LOCATION','Location'),('PROPERTY_DETAILS','Property Details'),('SPACE_DETAILS','Space Details'),('AMENITIES','Amenities'),('MEDIA','Media'),('PRICING','Pricing'),('AVAILABILITY','Availability'),('PREVIEW','Preview'),('PUBLISH','Publish')], default='PROPERTY_TYPE', max_length=30)),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('listing', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='draft', to='marketplace.listing')),
        ]),
        migrations.AddConstraint(model_name='listingmedia', constraint=models.UniqueConstraint(condition=models.Q(('is_primary', True)), fields=('listing',), name='one_primary_listing_media')),
    ]
