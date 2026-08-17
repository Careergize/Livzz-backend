# Livzz Smart PG - Complete API Implementation

## Base URL
```
http://localhost:8000/v1/
https://api.livzz.com/v1 (Production)
```

## Implementation Summary

This document outlines the complete API implementation based on the Livzz API specification.

### 1. Authentication & Onboarding (Global)

#### 1.1 Send OTP
- **Endpoint:** `POST /auth/send-otp/`
- **Permission:** AllowAny
- **Request Body:**
  ```json
  {
    "phone_number": "+919876543210"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "otp_reference_id": "ref_123456",
    "message": "OTP sent successfully"
  }
  ```

#### 1.2 Verify OTP
- **Endpoint:** `POST /auth/verify-otp/`
- **Permission:** AllowAny
- **Request Body:**
  ```json
  {
    "phone_number": "+919876543210",
    "otp": "123456",
    "otp_reference_id": "ref_123456"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "OTP verified successfully",
    "user_exists": false
  }
  ```

#### 1.3 Seeker Profile Setup
- **Endpoint:** `POST /auth/register/seeker/`
- **Content-Type:** multipart/form-data
- **Permission:** AllowAny
- **Required Fields:**
  - `first_name`, `email`, `phone_number`, `identity_type`
  - `identity_front_image` (File), `identity_back_image` (File)
- **Optional Fields:**
  - `whatsapp_number`, `profile_image` (File)
- **Response (201 CREATED):**
  ```json
  {
    "success": true,
    "message": "Seeker profile created successfully",
    "user": {...}
  }
  ```

#### 1.4 Owner Profile Setup
- **Endpoint:** `POST /auth/register/owner/`
- **Content-Type:** multipart/form-data
- **Permission:** AllowAny
- **Required Fields:**
  - `first_name`, `phone_number`, `upi_id`, `payee_name`, `identity_type`
  - `identity_front_image` (File), `identity_back_image` (File)
- **Optional Fields:**
  - `email`, `whatsapp_number`, `organization_name`, `profile_image` (File)

### 2. Seeker (Tenant) Module

#### 2.1 Fetch Nearby Properties
- **Endpoint:** `GET /seeker/properties/nearby/`
- **Query Parameters:** `lat`, `lng`, `radius_km`
- **Permission:** AllowAny
- **Example:** `/v1/seeker/properties/nearby/?lat=12.9716&lng=77.5946&radius_km=10`

#### 2.2 Search & Filter Properties
- **Endpoint:** `GET /seeker/properties/search/`
- **Query Parameters:**
  - `query` - Search text (e.g., "Stanza", "Indiranagar")
  - `location` - Location name
  - `property_type` - PG, Co-living, Rented Building, Room
  - `gender_filter` - Men, Women, Unisex
  - `budget_min`, `budget_max` - Price range

#### 2.3 Fetch Property Details
- **Endpoint:** `GET /seeker/properties/{property_id}/`
- **Permission:** AllowAny

#### 2.4 Fetch Current Stay Details
- **Endpoint:** `GET /seeker/stay/current/`
- **Permission:** IsAuthenticated

#### 2.5 Edit Seeker Profile
- **Endpoint:** `PATCH /seeker/profile/edit/`
- **Permission:** IsAuthenticated
- **Content-Type:** multipart/form-data
- **Optional Fields:** `name`, `email`, `whatsapp_number`, `profile_image`

#### 2.6 Fetch Booking History
- **Endpoint:** `GET /seeker/bookings/history/`
- **Query Parameters:** `status` (active, upcoming, past)
- **Permission:** IsAuthenticated

#### 2.7 Raise Maintenance Issue
- **Endpoint:** `POST /seeker/maintenance/raise/`
- **Permission:** IsAuthenticated
- **Request Body:**
  - `property_id`, `category`, `description`, `image_urls` (array)

### 3. Owner (Host) Module

#### 3.1 Fetch Dashboard Summary
- **Endpoint:** `GET /owner/dashboard/summary/`
- **Permission:** IsAuthenticated
- **Returns:** KPIs, active properties, tenants, maintenance stats

#### 3.2 Create/Edit Property
- **Create:** `POST /owner/properties/`
- **Update:** `PUT /owner/properties/{property_id}/`
- **Content-Type:** multipart/form-data
- **Permission:** IsAuthenticated
- **Required Fields:** `name`, `property_type`, `location`, `address`, `city`, `state`
- **Optional Fields:** `description`, `amenities` (JSON array), `property_images`, `room_configs`

#### 3.3 Search Users
- **Endpoint:** `GET /owner/users/search/`
- **Query Parameters:** `phone_number`
- **Permission:** IsAuthenticated

#### 3.4 Add Tenant
- **Endpoint:** `POST /owner/tenants/`
- **Content-Type:** multipart/form-data
- **Permission:** IsAuthenticated
- **Required Fields:**
  - `full_name`, `phone`, `email`, `property_id`, `room_number`
  - `rent`, `deposit`, `joining_date`, `payment_status`
  - `identity_type`, `identity_front_image`, `identity_back_image`

#### 3.5 Fetch Payments & Dues
- **Endpoint:** `GET /owner/payments/`
- **Query Parameters:** `property_id` (optional), `from_date`, `to_date`
- **Permission:** IsAuthenticated

#### 3.6 Manage Maintenance Tickets
- **Fetch:** `GET /owner/maintenance/`
- **Update:** `PATCH /owner/maintenance/{ticket_id}/`
- **Permission:** IsAuthenticated

### 4. Global Endpoints

#### 4.1 Fetch Locations
- **Endpoint:** `GET /locations/`
- **Permission:** AllowAny
- **Returns:** List of all locations for dropdown/autocomplete

## Models Created/Updated

### accounts.models.User
- Added: `phone_number`, `whatsapp_number`, `otp`, `otp_reference_id`, `otp_verified`
- Added: `identity_type`, `identity_front_image`, `identity_back_image`
- Added: `profile_image`, `upi_id`, `payee_name`, `organization_name`

### property.models.Property
- Added: `Location` foreign key
- Added: `latitude`, `longitude`, `description`, `amenities` (JSON)
- Added: `gender_filter`
- Updated: More detailed structure

### property.models.Location
- New model for storing location data with coordinates

### Tenant.models.Tenant
- Added: `whatsapp_number`, `profile_image`, `property` FK
- Added: `status` field

### Tenant.models.Booking
- New model to track booking history and current stays

### rooms.models.Room
- Updated: Changed `sharing_type` to CharField for better flexibility
- Added: `deposit` field, `updated_at` field

### payments.models.Payment
- Added: `payment_status`, `receipt_url`
- Updated: Better tracking of payment state

### maintenance.models.MaintenanceTicket
- Added: `tenant` FK
- Added: `image_urls` (JSON array)
- Updated: Improved status tracking

## Database Migrations

To apply all changes, run:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Testing the API

### Authentication Flow
1. Call `/v1/auth/send-otp/` with phone number
2. Get OTP from console/SMS (for now prints to console in DEBUG mode)
3. Call `/v1/auth/verify-otp/` with OTP and reference ID
4. Call `/v1/auth/register/seeker/` or `/v1/auth/register/owner/`

### Seeker Flow
1. Search properties: `/v1/seeker/properties/search/`
2. View details: `/v1/seeker/properties/{id}/`
3. Book property (via owner)
4. View current stay: `/v1/seeker/stay/current/`
5. Raise maintenance: `/v1/seeker/maintenance/raise/`

### Owner Flow
1. Dashboard: `/v1/owner/dashboard/summary/`
2. Create property: `/v1/owner/properties/`
3. Add tenant: `/v1/owner/tenants/`
4. View payments: `/v1/owner/payments/`
5. Manage maintenance: `/v1/owner/maintenance/`

## Important Notes

1. **CORS:** Currently set to allow all origins. Update `CORS_ALLOWED_ORIGINS` in settings for production.

2. **Media Files:** All file uploads are stored in `/media/` directory. Configure proper storage in production (S3, etc.)

3. **OTP:** Currently prints to console in DEBUG mode. Integrate with actual SMS provider (Twilio, AWS SNS, etc.)

4. **Authentication:** Implement JWT tokens or Django REST authentication for production.

5. **Pagination:** Consider adding pagination for large result sets.

6. **Rate Limiting:** Add rate limiting for authentication endpoints.

7. **Image Processing:** Consider adding image optimization/compression middleware.

## Next Steps

1. Integrate SMS gateway for OTP delivery
2. Implement JWT token authentication
3. Add input validation and error handling
4. Create management commands for data initialization
5. Add comprehensive logging
6. Implement caching for frequently accessed data
7. Add API versioning strategy
8. Create comprehensive API documentation (Swagger/OpenAPI)
