# Livzz Smart PG - Setup & Installation Guide

## Prerequisites
- Python 3.8+
- pip
- virtualenv (recommended)

## Installation Steps

### 1. Create and Activate Virtual Environment
```bash
cd d:/Projects/LIVZZ/SMART_PG/smart_pg

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

If requirements.txt is missing or incomplete, install essential packages:
```bash
pip install Django==4.2.0
pip install djangorestframework==3.14.0
pip install django-cors-headers==4.0.0
pip install Pillow==9.5.0
pip install python-decouple==3.8
```

### 3. Create Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (Admin)
```bash
python manage.py createsuperuser
# Enter credentials when prompted
```

### 5. Create Locations
```bash
python manage.py shell
```

Then in the Python shell:
```python
from property.models import Location

# Create sample locations
locations_data = [
    {'name': 'Indiranagar', 'city': 'Bangalore', 'state': 'Karnataka', 'latitude': 12.9716, 'longitude': 77.6412},
    {'name': 'Koramangala', 'city': 'Bangalore', 'state': 'Karnataka', 'latitude': 12.9352, 'longitude': 77.6245},
    {'name': 'Stanza Living', 'city': 'Bangalore', 'state': 'Karnataka', 'latitude': 12.9690, 'longitude': 77.6450},
    {'name': 'Whitefield', 'city': 'Bangalore', 'state': 'Karnataka', 'latitude': 12.9698, 'longitude': 77.7499},
]

for loc_data in locations_data:
    Location.objects.get_or_create(**loc_data)

print("Locations created successfully!")
exit()
```

### 6. Run Development Server
```bash
python manage.py runserver
```

Server will start at: `http://localhost:8000`

## File Structure

```
smart_pg/
├── accounts/              # Authentication & User Management
│   ├── models.py         # User model with OTP, identity fields
│   ├── views.py          # Auth views (OTP, register, login)
│   ├── serializers.py    # Auth serializers
│   ├── urls.py           # Auth URLs
│
├── property/             # Properties Management
│   ├── models.py         # Property, Location, RoomConfiguration
│   ├── views.py          # Original views
│   ├── seeker_views.py   # Seeker/Tenant views (new)
│   ├── owner_views.py    # Owner/Host views (new)
│   ├── global_views.py   # Global views (locations)
│   ├── serializers.py    # Property serializers
│   ├── urls.py           # All property-related URLs
│
├── Tenant/               # Tenant/Booking Management
│   ├── models.py         # Tenant, Booking models
│   ├── serializers.py    # Tenant, Booking serializers
│
├── rooms/                # Room Management
│   ├── models.py         # Room model
│
├── payments/             # Payment & Financial Management
│   ├── models.py         # Payment, Complaint, Notification
│   ├── serializers.py    # Payment serializers
│
├── maintenance/          # Maintenance Ticket Management
│   ├── models.py         # MaintenanceTicket model
│   ├── serializers.py    # Maintenance serializers
│
├── staff/                # Staff Management
│   ├── models.py         # Staff model
│
├── visitor/              # Visitor Management
│   ├── models.py         # Visitor model
│
├── smart_pg/
│   ├── settings.py       # Django settings
│   ├── urls.py           # Main URL routing (updated for v1/)
│   ├── wsgi.py
│
├── media/                # Media files (uploaded by users)
├── requirements.txt      # Python dependencies
└── API_IMPLEMENTATION.md # API documentation
```

## API Testing

### Using cURL

#### Send OTP
```bash
curl -X POST http://localhost:8000/v1/auth/send-otp/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210"}'
```

#### Verify OTP
```bash
curl -X POST http://localhost:8000/v1/auth/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210", "otp": "123456", "otp_reference_id": "ref_123456"}'
```

#### Register Seeker
```bash
curl -X POST http://localhost:8000/v1/auth/register/seeker/ \
  -F "first_name=John" \
  -F "email=john@example.com" \
  -F "phone_number=+919876543210" \
  -F "whatsapp_number=+919876543210" \
  -F "identity_type=Aadhar" \
  -F "identity_front_image=@path/to/front.jpg" \
  -F "identity_back_image=@path/to/back.jpg"
```

### Using Postman

1. Import the API endpoints from API_IMPLEMENTATION.md
2. Set up collections for:
   - Authentication
   - Seeker Operations
   - Owner Operations
   - Global Endpoints

## Configuration

### Settings.py Updates
The following have been configured:
- `AUTH_USER_MODEL = 'accounts.User'` - Custom User model
- `CORS_ALLOW_ALL_ORIGINS = True` - CORS enabled for all origins
- `MEDIA_URL = '/media/'` - Media file serving
- Installed apps include all custom apps

### Environment Variables (Recommended for Production)
Create a `.env` file:
```
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=api.livzz.com,www.livzz.com
DATABASE_URL=postgresql://user:password@localhost/livzz_db
SMS_PROVIDER_API_KEY=your-sms-api-key
```

## Common Issues & Solutions

### Issue: Import errors for models
**Solution:** Ensure you've run migrations:
```bash
python manage.py migrate
```

### Issue: CORS errors
**Solution:** Update CORS settings in settings.py for your frontend domain.

### Issue: Media files not serving
**Solution:** Ensure DEBUG=True or configure static/media serving in production web server.

### Issue: OTP not received
**Solution:** In DEBUG mode, OTP prints to console. For production, integrate SMS gateway:
- Twilio
- AWS SNS
- Custom SMS provider API

### Issue: Database locked
**Solution:** Delete `db.sqlite3` and re-run migrations if using SQLite in development.

## Production Deployment

### 1. Update Settings
- Set `DEBUG = False`
- Update `ALLOWED_HOSTS`
- Use environment variables for secrets
- Configure static/media file storage (AWS S3 recommended)

### 2. Database
- Use PostgreSQL or MySQL instead of SQLite
- Set up proper database backups

### 3. Web Server
- Use Gunicorn + Nginx
- Configure SSL/HTTPS
- Set up proper logging

### 4. Additional Services
- Integrate SMS gateway for OTP
- Set up email service
- Configure image CDN for media files
- Implement caching (Redis)

## Admin Panel

Access Django admin at: `http://localhost:8000/admin/`

You can manage:
- Users and authentication
- Properties
- Rooms
- Tenants
- Payments
- Maintenance tickets
- Staff
- Locations

## Support & Documentation

Refer to:
- `API_IMPLEMENTATION.md` - Complete API documentation
- `Livzz_API_Documentation.html` - Original API spec (provided)
- Django docs: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/

## Next Steps

1. ✅ Models created and updated
2. ✅ Serializers implemented
3. ✅ Views created
4. ✅ URLs configured
5. ⏳ Test all endpoints
6. ⏳ Integrate SMS provider
7. ⏳ Add JWT authentication
8. ⏳ Deploy to production
