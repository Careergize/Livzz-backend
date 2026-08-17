# Models Summary & Relationships

## Updated & New Models

### 1. accounts.models.User (Extended from AbstractUser)

**Fields:**
- `phone_number` - CharField, unique
- `whatsapp_number` - CharField, optional
- `role` - Choices: owner, staff, tenant, seeker
- `otp` - CharField (for OTP during registration)
- `otp_reference_id` - CharField (OTP reference)
- `otp_verified` - Boolean (verification status)
- `identity_type` - Choices: Aadhar, PAN, Passport, Driving License
- `identity_front_image` - ImageField
- `identity_back_image` - ImageField
- `profile_image` - ImageField
- `upi_id` - CharField (for owners/payment)
- `payee_name` - CharField (for owners)
- `organization_name` - CharField (for owners)

**Methods:**
- `is_owner()`
- `is_staff_user()`
- `is_tenant()`
- `is_seeker()`

---

### 2. property.models.Location (NEW)

**Fields:**
- `name` - CharField, unique (e.g., "Indiranagar", "Koramangala")
- `city` - CharField
- `state` - CharField
- `latitude` - FloatField (optional)
- `longitude` - FloatField (optional)

**Relationships:**
- One-to-Many: Properties

---

### 3. property.models.Property (UPDATED)

**Fields:**
- `owner` - ForeignKey to User
- `name` - CharField
- `property_type` - Choices: PG, Co-living, Rented Building, Room, Hostel
- `location` - ForeignKey to Location (NEW)
- `address` - TextField
- `city` - CharField
- `state` - CharField
- `latitude` - FloatField (NEW)
- `longitude` - FloatField (NEW)
- `description` - TextField (NEW)
- `amenities` - JSONField array (NEW)
- `price` - DecimalField
- `rating` - FloatField
- `image` - ImageField
- `total_rooms` - PositiveIntegerField
- `gender_filter` - Choices: Men, Women, Unisex (NEW)
- `is_active` - Boolean
- `created_at` - DateTimeField (NEW)
- `updated_at` - DateTimeField (NEW)

**Relationships:**
- ForeignKey: User (owner)
- ForeignKey: Location
- Reverse: rooms, room_configs, bookings, maintenance_tickets, tenants

---

### 4. property.models.RoomConfiguration (UPDATED)

**Fields:**
- `property` - ForeignKey to Property
- `room_type` - Choices: Single Sharing, Double Sharing, Triple Sharing, Four Sharing, Single
- `rent` - DecimalField (NEW - replaces price_per_bed)
- `deposit` - DecimalField (NEW)
- `total_beds` - PositiveIntegerField
- `available_beds` - PositiveIntegerField
- `room_image` - ImageField

---

### 5. rooms.models.Room (UPDATED)

**Fields:**
- `property` - ForeignKey to Property
- `room_number` - CharField
- `sharing_type` - CharField (changed from Integer choices - more flexible)
- `total_beds` - IntegerField
- `occupied_beds` - IntegerField
- `rent` - DecimalField
- `deposit` - DecimalField (NEW)
- `is_active` - Boolean
- `created_at` - DateTimeField
- `updated_at` - DateTimeField (NEW)

**Methods:**
- `available_beds()` - Returns available beds
- `is_full()` - Returns if room is full

---

### 6. Tenant.models.Tenant (UPDATED)

**Fields:**
- `user` - OneToOneField to User (nullable, related_name='tenant_profile')
- `full_name` - CharField
- `phone` - CharField
- `whatsapp_number` - CharField (NEW)
- `email` - EmailField
- `room` - ForeignKey to Room
- `property` - ForeignKey to Property (NEW)
- `join_date` - DateField
- `rent_date` - DateField
- `security_deposit` - DecimalField
- `monthly_rent` - DecimalField
- `id_proof_type` - Choices
- `id_proof_image` - ImageField
- `profile_image` - ImageField (NEW)
- `is_paid` - Boolean
- `status` - Choices: active, inactive (NEW)
- `created_at` - DateTimeField
- `updated_at` - DateTimeField (NEW)

---

### 7. Tenant.models.Booking (NEW)

**Fields:**
- `booking_id` - CharField, unique (e.g., "BK-8902")
- `tenant` - ForeignKey to Tenant
- `property` - ForeignKey to Property
- `room` - ForeignKey to Room
- `room_type` - CharField
- `check_in_date` - DateField
- `check_out_date` - DateField (nullable)
- `monthly_rent` - DecimalField
- `deposit` - DecimalField
- `status` - Choices: active, upcoming, past, cancelled
- `created_at` - DateTimeField
- `updated_at` - DateTimeField

---

### 8. payments.models.Payment (UPDATED)

**Fields:**
- `tenant` - ForeignKey to Tenant
- `property` - ForeignKey to Property
- `transaction_id` - CharField, unique (NEW)
- `amount` - DecimalField
- `payment_date` - DateTimeField
- `payment_method` - Choices: UPI, CASH, TRANSFER
- `payment_status` - Choices: SUCCESSFUL, FAILED, PENDING (NEW)
- `month_for` - CharField
- `notes` - TextField
- `receipt_url` - URLField (NEW)
- `created_at` - DateTimeField
- `updated_at` - DateTimeField (NEW)

---

### 9. payments.models.Complaint

**Fields:**
- `tenant` - ForeignKey to Tenant
- `title` - CharField
- `description` - TextField
- `reply` - TextField
- `status` - Choices: PENDING, RESOLVED, IN_PROGRESS
- `created_at` - DateTimeField
- `updated_at` - DateTimeField (NEW)

---

### 10. payments.models.Notification

**Fields:**
- `tenant` - ForeignKey to Tenant
- `message` - TextField
- `notification_type` - Choices: PAYMENT, COMPLAINT, REPLY, MAINTENANCE
- `is_read` - Boolean
- `created_at` - DateTimeField

---

### 11. maintenance.models.MaintenanceTicket (UPDATED)

**Fields:**
- `property` - ForeignKey to Property
- `tenant` - ForeignKey to Tenant (NEW)
- `assigned_staff` - ForeignKey to Staff
- `ticket_id` - CharField, unique, auto-generated
- `category` - Choices: Plumbing, Electrical, Furniture, Security, General
- `room_number` - CharField (NEW, replaces unit_details)
- `description` - TextField
- `image_urls` - JSONField array (NEW)
- `priority` - Choices: LOW, MEDIUM, HIGH
- `status` - Choices: Pending, In Progress, Resolved
- `repair_cost` - DecimalField
- `created_at` - DateTimeField
- `updated_at` - DateTimeField (NEW)
- `resolved_at` - DateTimeField

---

### 12. staff.models.Staff

**Fields:**
- `property` - ForeignKey to Property
- `name` - CharField
- `role` - Choices: Kitchen, Takecare, Security, Manager, Cleaning
- `email` - EmailField, unique
- `phone` - CharField
- `status` - Choices: Active, On Leave
- `joined_at` - DateField
- `salary_amount` - DecimalField
- `is_paid` - Boolean
- `last_paid_date` - DateField

---

### 13. visitor.models.Visitor

**Fields:**
- `property` - ForeignKey to Property
- `room` - ForeignKey to Room
- `full_name` - CharField
- `phone_number` - CharField
- `resident_name` - CharField
- `purpose` - Choices: Relative, Delivery, Maintenance, Guest
- `entry_time` - DateTimeField
- `exit_time` - DateTimeField
- `status` - Choices: Checked-In, Checked-Out

---

## Relationship Diagram

```
User (owner/tenant/seeker)
 ├── Property (owner)
 │    ├── Location
 │    ├── Room
 │    │    └── Tenant
 │    │         ├── Booking
 │    │         └── Payment
 │    ├── RoomConfiguration
 │    ├── MaintenanceTicket
 │    │    ├── Tenant
 │    │    └── Staff
 │    ├── Staff
 │    └── Visitor
 │         └── Room
 │
 └── Tenant
      ├── Room
      ├── Booking
      │    └── Property
      ├── Payment
      ├── Complaint
      ├── Notification
      └── MaintenanceTicket
```

## Database Diagram (Tables Created)

```
accounts_user
├── id (PK)
├── phone_number (UQ)
├── role
├── otp
├── otp_verified
├── identity_type
├── identity_front_image
├── identity_back_image
├── profile_image
├── upi_id
├── payee_name
├── organization_name

property_location
├── id (PK)
├── name (UQ)
├── city
├── state
├── latitude
├── longitude

property_property
├── id (PK)
├── owner_id (FK to accounts_user)
├── location_id (FK to property_location)
├── name
├── property_type
├── address
├── city
├── latitude
├── longitude
├── description
├── amenities (JSON)
├── price
├── rating
├── gender_filter

property_roomconfiguration
├── id (PK)
├── property_id (FK)
├── room_type
├── rent
├── deposit
├── total_beds
├── available_beds

rooms_room
├── id (PK)
├── property_id (FK)
├── room_number
├── sharing_type
├── total_beds
├── occupied_beds
├── rent
├── deposit

tenant_tenant
├── id (PK)
├── user_id (FK, nullable)
├── property_id (FK)
├── room_id (FK, nullable)
├── full_name
├── phone
├── whatsapp_number
├── email
├── join_date
├── security_deposit
├── monthly_rent
├── id_proof_type
├── id_proof_image

tenant_booking
├── id (PK)
├── booking_id (UQ)
├── tenant_id (FK)
├── property_id (FK)
├── room_id (FK, nullable)
├── room_type
├── check_in_date
├── check_out_date
├── monthly_rent
├── deposit
├── status

payments_payment
├── id (PK)
├── transaction_id (UQ)
├── tenant_id (FK)
├── property_id (FK)
├── amount
├── payment_date
├── payment_method
├── payment_status
├── month_for

maintenance_maintenanceticket
├── id (PK)
├── ticket_id (UQ)
├── property_id (FK)
├── tenant_id (FK, nullable)
├── assigned_staff_id (FK, nullable)
├── category
├── room_number
├── description
├── image_urls (JSON)
├── priority
├── status

staff_staff
├── id (PK)
├── property_id (FK)
├── name
├── role
├── email (UQ)
├── phone
├── salary_amount
├── is_paid

visitor_visitor
├── id (PK)
├── property_id (FK)
├── room_id (FK)
├── full_name
├── phone_number
├── resident_name
├── purpose
├── entry_time
├── exit_time
├── status
```

## Migration Strategy

To safely apply these changes:

```bash
# 1. Create migrations
python manage.py makemigrations

# 2. Review migrations
python manage.py showmigrations

# 3. Dry run (for testing)
python manage.py migrate --plan

# 4. Apply migrations
python manage.py migrate

# 5. Create initial data (locations)
python manage.py shell < init_locations.py
```
