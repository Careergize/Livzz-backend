from io import BytesIO

from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from PIL import Image, UnidentifiedImageError
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.models import ListerProfile
from api_v2.responses import data_response
from api_v2.views import V2APIView
from marketplace.models import Listing, ListingMedia, PropertyMedia
from marketplace.self_service import (create_listing_draft, drafts_for, reorder_media,
                                      update_listing_draft)
from marketplace.services import PublishValidationError, publish_listing

User = get_user_model()
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGES = 20
ALLOWED_FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}


def profile_data(user):
    profile = ListerProfile.objects.filter(user=user).first()
    return None if profile is None else {
        'lister_type': profile.lister_type, 'agency_name': profile.agency_name or None,
        'business_phone': profile.business_phone or None, 'business_email': profile.business_email or None,
        'registration_number': profile.registration_number or None,
        'verification_status': profile.verification_status,
    }


def user_data(user):
    return {'id': user.pk, 'name': user.get_full_name() or user.username, 'email': user.email,
            'phone_number': user.phone_number, 'lister_profile': profile_data(user)}


class RegisterView(V2APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone, password = request.data.get('phone_number'), request.data.get('password')
        email = request.data.get('email', '')
        if not phone or not password:
            raise ValidationError({'phone_number': 'phone_number and password are required.'})
        if len(password) < 8:
            raise ValidationError({'password': 'Password must contain at least 8 characters.'})
        if User.objects.filter(phone_number=phone).exists() or (email and User.objects.filter(email__iexact=email).exists()):
            raise ValidationError({'account': 'An account with these credentials already exists.'})
        user = User.objects.create_user(username=request.data.get('username') or phone,
                                        phone_number=phone, password=password, email=email,
                                        first_name=request.data.get('first_name', ''),
                                        last_name=request.data.get('last_name', ''))
        token = Token.objects.create(user=user)
        return data_response({'token': token.key, 'user': user_data(user)}, status=201)


class LoginView(V2APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identity, password = request.data.get('phone_number') or request.data.get('username'), request.data.get('password')
        user = User.objects.filter(phone_number=identity).first()
        user = authenticate(request, username=user.username if user else identity, password=password)
        if user is None:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Invalid credentials.')
        token, _ = Token.objects.get_or_create(user=user)
        return data_response({'token': token.key, 'user': user_data(user)})


class LogoutView(V2APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return data_response({'logged_out': True})


class ListerProfileView(V2APIView):
    permission_classes = [IsAuthenticated]
    allowed = {'lister_type', 'agency_name', 'business_phone', 'business_email', 'registration_number'}

    def post(self, request):
        if ListerProfile.objects.filter(user=request.user).exists():
            raise ValidationError({'lister_profile': 'Profile already exists; use PATCH.'})
        return self._save(request, create=True)

    def patch(self, request):
        return self._save(request, create=False)

    def _save(self, request, create):
        forbidden = set(request.data) - self.allowed
        if forbidden:
            raise ValidationError({field: 'This field cannot be modified.' for field in forbidden})
        kind = request.data.get('lister_type')
        if kind and kind not in dict(ListerProfile.LISTER_TYPES):
            raise ValidationError({'lister_type': 'Use OWNER, BROKER, or PROPERTY_MANAGER.'})
        if create and not kind:
            raise ValidationError({'lister_type': 'This field is required.'})
        profile, _ = ListerProfile.objects.get_or_create(user=request.user,
                                                          defaults={'lister_type': kind or ListerProfile.OWNER})
        for field in self.allowed:
            if field in request.data:
                setattr(profile, field, request.data[field])
        profile.full_clean()
        profile.save()
        return data_response(profile_data(request.user), status=201 if create else 200)


def draft_data(draft, request=None):
    listing, prop = draft.listing, draft.listing.property
    media = [{'id': item.id, 'url': request.build_absolute_uri((item.property_media.file if item.property_media_id else item.file).url),
              'sort_order': item.sort_order, 'is_primary': item.is_primary, 'caption': item.caption}
             for item in listing.media_items.select_related('property_media').all()]
    relation = {'PG': 'pgdetails', 'APARTMENT': 'apartmentdetails',
                'VILLA': 'villadetails', 'OFFICE': 'officedetails'}[prop.property_type]
    details = getattr(prop, relation, None)
    category_details = None if details is None else {
        field.name: getattr(details, field.name) for field in details._meta.fields
        if field.name not in {'id', 'property'}}
    target = listing.target
    price = listing.price_plans.filter(status='ACTIVE').order_by('-effective_from').first()
    availability = listing.availability_records.order_by('start', 'id').first()
    return {'draft_id': str(draft.public_id), 'property_id': str(prop.public_id),
            'listing_id': str(listing.public_id), 'status': listing.status,
            'current_step': draft.current_step, 'title': listing.title,
            'description': listing.description, 'property_type': prop.property_type,
            'property': {'name': prop.name, 'description': prop.description,
                         'address': prop.address, 'locality': prop.locality,
                         'city': prop.city, 'state': prop.state, 'country': prop.country,
                         'postal_code': prop.postal_code, 'latitude': prop.latitude, 'longitude': prop.longitude},
            'category_details': category_details,
            'amenities': list(prop.property_amenities.values_list('amenity__code', flat=True)),
            'target': {'target_type': target.target_type,
                       'unit_id': str(target.unit.public_id) if target.unit_id else None,
                       'inventory_item_id': str(target.inventory_item.public_id) if target.inventory_item_id else None,
                       'capacity': target.capacity},
            'pricing': None if price is None else {
                'amount': str(price.amount), 'currency': price.currency,
                'billing_cycle': price.billing_cycle, 'deposit_amount': str(price.deposit_amount),
                'maintenance_amount': str(price.maintenance_amount) if price.maintenance_amount is not None else None,
                'minimum_stay': price.minimum_stay, 'effective_from': price.effective_from.isoformat(),
                'effective_to': price.effective_to.isoformat() if price.effective_to else None},
            'availability': None if availability is None else {
                'status': availability.status, 'start': availability.start.isoformat(),
                'end': availability.end.isoformat() if availability.end else None,
                'quantity': availability.quantity},
            'media': media}


class DraftListCreateView(V2APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return data_response([draft_data(item, request) for item in drafts_for(request.user)])
    def post(self, request):
        draft = create_listing_draft(user=request.user, property_type=request.data.get('property_type'),
                                     title=request.data.get('title', ''))
        return data_response(draft_data(draft, request), status=201)


class DraftDetailView(V2APIView):
    permission_classes = [IsAuthenticated]
    def object(self, request, draft_id):
        return get_object_or_404(drafts_for(request.user), public_id=draft_id)
    def get(self, request, draft_id):
        return data_response(draft_data(self.object(request, draft_id), request))
    def patch(self, request, draft_id):
        draft = update_listing_draft(user=request.user, draft=self.object(request, draft_id), data=request.data)
        return data_response(draft_data(draft, request))


class MyListingsView(V2APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        listings = Listing.objects.filter(created_by=request.user).select_related('property')
        return data_response([{'id': str(x.public_id), 'title': x.title, 'status': x.status,
                               'property_id': str(x.property.public_id), 'category': x.category} for x in listings])


class DraftPublishView(DraftDetailView):
    def post(self, request, draft_id):
        draft = self.object(request, draft_id)
        try:
            listing = publish_listing(user=request.user, listing=draft.listing)
        except PublishValidationError as exc:
            from rest_framework.response import Response
            grouped = {}
            for error in exc.errors:
                grouped.setdefault(error['field'], []).append(error['message'])
            return Response({'errors': grouped}, status=400)
        return data_response({'listing_id': str(listing.public_id), 'status': listing.status})


def validate_image(upload):
    if upload.size > MAX_IMAGE_BYTES:
        raise ValidationError({'images': f'Each image must be at most {MAX_IMAGE_BYTES // 1024 // 1024} MB.'})
    try:
        image = Image.open(upload)
        image.verify()
        detected = ALLOWED_FORMATS.get(image.format)
    except (UnidentifiedImageError, OSError):
        detected = None
    finally:
        upload.seek(0)
    if not detected or upload.content_type != detected:
        raise ValidationError({'images': 'Only genuine JPEG, PNG, or WEBP images are accepted.'})


class DraftMediaView(DraftDetailView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    def get(self, request, draft_id):
        return data_response(draft_data(self.object(request, draft_id), request)['media'])
    @transaction.atomic
    def post(self, request, draft_id):
        draft = self.object(request, draft_id)
        uploads = request.FILES.getlist('images')
        if not uploads:
            raise ValidationError({'images': 'Upload one or more images.'})
        if draft.listing.media_items.count() + len(uploads) > MAX_IMAGES:
            raise ValidationError({'images': f'A listing may contain at most {MAX_IMAGES} images.'})
        for upload in uploads:
            validate_image(upload)
        start = draft.listing.media_items.count()
        for offset, upload in enumerate(uploads):
            prop_media = PropertyMedia.objects.create(property=draft.listing.property, file=upload,
                                                       media_type='IMAGE', sort_order=start + offset,
                                                       is_primary=(start == 0 and offset == 0))
            ListingMedia.objects.create(listing=draft.listing, property_media=prop_media,
                                        sort_order=start + offset, is_primary=(start == 0 and offset == 0))
        return data_response(draft_data(draft, request)['media'], status=201)
    def patch(self, request, draft_id):
        draft = self.object(request, draft_id)
        ids = request.data.get('media_ids')
        if not isinstance(ids, list) or len(ids) != draft.listing.media_items.count():
            raise ValidationError({'media_ids': 'Provide every media id in the desired order.'})
        reorder_media(listing=draft.listing, media_ids=ids, primary_id=request.data.get('primary_id'))
        return data_response(draft_data(draft, request)['media'])


class DraftMediaDetailView(DraftDetailView):
    @transaction.atomic
    def delete(self, request, draft_id, media_id):
        draft = self.object(request, draft_id)
        item = get_object_or_404(ListingMedia.objects.select_related('property_media'), listing=draft.listing, id=media_id)
        prop_media = item.property_media
        item.delete()
        if prop_media and not prop_media.listing_uses.exists():
            prop_media.file.delete(save=False)
            prop_media.delete()
        remaining = draft.listing.media_items.order_by('sort_order', 'id')
        if remaining.exists() and not remaining.filter(is_primary=True).exists():
            ListingMedia.objects.filter(pk=remaining.first().pk).update(is_primary=True)
        return data_response({'deleted': True})
