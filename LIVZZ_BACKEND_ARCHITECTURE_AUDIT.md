# Livzz Backend Architecture Audit

**Status:** architecture proposal only; no implementation has been performed  
**Audit date:** 2026-08-31  
**Scope inspected:** Django settings, models, serializers, views, URL configuration, signals, migrations, bundled SQLite schema, and repository documentation. No frontend source project is present in this checkout, so frontend contracts below are inferred from the live REST routes and serializers; client-side usage could not be verified.

## Executive summary

The existing code is already a Django modular monolith and should remain one. Its app separation is a useful starting point, but its data model is a single-owner PG management system rather than the requested multi-organization property platform.

The most important changes are:

1. Keep `accounts.User` as identity, but stop using its single `role` field for authorization. Add organization membership and scoped roles.
2. Keep one canonical `Property`, move ownership to `Organization`, and add extensible category detail tables for PG, apartment, villa, and office.
3. Separate the physical asset hierarchy (`Property -> Unit/Space -> InventoryItem`) from market offers (`Listing`, `ListingPrice`, `Availability`).
4. Replace `Tenant` as the current-stay record with a reusable person/customer profile plus time-bounded `Tenancy` and `OccupancyAssignment` records.
5. Replace aggregate bed counters and duplicated room concepts with explicit units and optionally assignable inventory such as beds.
6. Replace the rent-month payment shortcut with invoices/charges, payment transactions, and allocations; introduce a general document model.
7. Put all management queries behind organization/property scoped authorization. The current global `AllowAny` default exposes many create/update/delete APIs.
8. Introduce a versioned `/api/v2/` contract while maintaining `/api/v1/` compatibility adapters during migration.

There is no need for microservices. A PostgreSQL-backed modular monolith with domain services, explicit permissions, database constraints, and indexed tenant/organization scoping is sufficient for the stated scale.

## 1. Existing Django models

| App | Model | Purpose and important fields |
|---|---|---|
| `accounts` | `User(AbstractUser)` | Login identity; unique phone, OTP state, identity images, profile image, single `role`, and owner payment/organization fields (`upi_id`, `payee_name`, `organization_name`). |
| `property` | `Location` | Named locality with city/state and optional latitude/longitude. |
| `property` | `Property` | Physical property and marketplace presentation combined: direct `owner`, type, address/geolocation, JSON amenities, price, rating, one image, room count, gender filter, active flag. |
| `property` | `RoomConfiguration` | Market-like sharing configuration per property with rent/deposit, aggregate bed counts, and image. |
| `rooms` | `Room` | Physical room per property with sharing type, aggregate beds/occupied beds, rent/deposit, and active flag. |
| `Tenant` | `Tenant` | Person profile and current occupancy combined; optional one-to-one user, direct room/property, dates, rent/deposit, identity image, and one `is_paid` flag. |
| `Tenant` | `Booking` | Stay record linked to tenant/property/room with dates, rent/deposit, room type, and status. |
| `payments` | `Payment` | Rent-like transaction linked directly to tenant and property; amount, status/method, free-text `month_for`, receipt URL. |
| `payments` | `Complaint` | Tenant complaint with reply and status. |
| `payments` | `Notification` | Tenant-only notification with type, message, and read flag. |
| `maintenance` | `MaintenanceTicket` | Property ticket optionally linked to tenant and staff; category, free-text room number, images JSON, priority/status/cost. |
| `visitor` | `Visitor` | Property/room visitor log; resident is stored as text rather than a tenant/occupancy relation. |
| `staff` | `Staff` | Non-user employee record tied to one property; operational role, contact data, salary and coarse paid state. |
| `grocery` | `GroceryExpense` | Property expense with vendor/category/method/status and receipt image. |

The SQLite database contains tables for all the models above. Migration files are initial/simple migrations; there is no organization, listing, inventory, document, enquiry, lead, or visit-request table.

## 2. Existing relationships

```text
User 1 ───< Property
User 0..1 ─── 0..1 Tenant

Location 0..1 ───< Property
Property 1 ───< RoomConfiguration
Property 1 ───< Room
Property 0..1 ───< Tenant
Room     0..1 ───< Tenant

Tenant   1 ───< Booking >─── 1 Property
                         >─── 0..1 Room
Tenant   1 ───< Payment >─── 1 Property
Tenant   1 ───< Complaint
Tenant   1 ───< Notification

Property 1 ───< MaintenanceTicket >─── 0..1 Tenant
                                  >─── 0..1 Staff
Property 1 ───< Staff
Property 1 ───< Visitor >─── 1 Room
Property 1 ───< GroceryExpense
```

Important integrity gaps:

- Nothing enforces that a tenant's room belongs to the tenant's property.
- Nothing enforces that a booking's room and tenant belong to its property.
- Nothing enforces that a payment's tenant belongs to its property.
- Nothing enforces that visitor room, assigned staff, or maintenance tenant belong to the ticket/visitor property.
- `Room.room_number` is not unique within a property.
- `RoomConfiguration` and `Room` overlap but have no relationship.
- Capacity values are mutable counters without constraints or assignment records.

## 3. Existing API endpoints and observable data contracts

DRF Token and Session authentication are configured. Unless a view explicitly overrides permissions, the global permission is `AllowAny`.

### Canonical routes

| Method(s) | Route | Current behavior / contract |
|---|---|---|
| POST | `/auth/send-otp/` | Accepts `phone_number`; returns success and OTP reference. Creates a user stub. |
| POST | `/auth/verify-otp/` | Accepts phone, OTP, reference; marks OTP verified. |
| POST | `/auth/register/seeker/` | Multipart seeker profile; overwrites `User.role=seeker`. |
| POST | `/auth/register/owner/` | Multipart owner profile/payment data; overwrites `User.role=owner`. |
| POST | `/auth/login/` | Phone/password login; returns token and serialized user including `role`. |
| POST | `/auth/logout/` | Authenticated token deletion. |
| GET | `/properties/nearby/` | Public active properties by `lat`, `lng`, optional radius. |
| GET | `/properties/search/` | Public property search: query, location, property type, gender, property-level price range. |
| GET | `/properties/{property_id}/` | Public property detail, rooms/configurations, owner contact, related properties. |
| GET | `/stay/current/` | Authenticated current active booking and payment/ticket summary. |
| GET | `/bookings/history/` | Authenticated booking history. |
| PATCH | `/profile/edit/` | Authenticated user profile update. |
| POST | `/maintenance/raise/` | Authenticated tenant ticket creation. |
| GET | `/dashboard/summary/` | Authenticated direct-owner aggregate dashboard. |
| GET, POST | `/properties/` | Owner management view, but its permission declaration is commented out; GET returns every property. POST relies on `request.user`. |
| PUT | `/owner/properties/{property_id}/` | Updates a directly owned property. |
| GET | `/users/search/?phone_number=` | Authenticated global user lookup. |
| POST | `/tenants/` | Because of URL ordering, this resolves to owner `AddTenantView`, not the generic tenant view. |
| GET | `/payments/` | Because of URL ordering, this resolves to authenticated owner payment summary, not generic payment CRUD. |
| GET | `/maintenance/` | Authenticated direct-owner tickets. |
| PATCH | `/maintenance/{ticket_id}/` | Authenticated direct-owner ticket update. |
| GET | `/bookings/` | Authenticated direct-owner bookings, optional status/property filters. |
| PATCH | `/bookings/{booking_id}/` | Authenticated direct-owner booking status update. |
| GET | `/locations/` | Location list. |
| GET, POST | `/rooms/` | Public/global room list and create. |
| GET, PATCH, DELETE | `/rooms/{id}/` | Public/global room CRUD. |
| GET, POST | `/visitors/` | Public/global visitor list/create; optional `property_id`. |
| PATCH | `/visitors/{id}/` | Public/global visitor update/check-out. |
| GET, POST | `/staff/` | Public/global staff list/create; optional `property_id`. |
| GET, PATCH, DELETE | `/staff/{id}/` | Public/global staff CRUD. |
| GET, POST | `/expenses/` | Public/global property expense list/create; optional `property_id`. |
| PATCH, DELETE | `/expenses/{id}/` | Public/global expense update/delete. |
| GET, POST | `/tickets/` | Public/global maintenance ticket list/create; optional `property_id`. |
| PATCH, DELETE | `/tickets/{id}/` | Public/global ticket update/delete. |
| GET, POST | `/complaints/` | Public/global complaint list/create. |
| PATCH | `/complaints/{id}/reply/` | Public/global complaint reply. |
| GET, POST | `/notifications/` | GET exposes all; POST marks every unread notification read. |

### Route aliasing and shadowing

`property.urls` is mounted at `/`, `/seeker/`, and `/locations/`. Every route in that module therefore has three forms, such as `/properties/search/`, `/seeker/properties/search/`, and `/locations/properties/search/`. Its empty route also produces `/`, `/seeker/`, and `/locations/` location lists. This is accidental API surface and a compatibility risk.

Several later root URL includes declare paths already claimed by `property.urls`. Django resolves the earlier match, so generic `Tenant` and `payments.Payment` list/create routes at `/tenants/` and `/payments/` are shadowed. `property.views.PropertyListView` and `PropertyDetailAPIView` are not wired at all.

### Frontend-facing payload characteristics

- Property search/list objects mix asset and offer fields: `price`, `amenities`, `rating`, `gender_filter`, `total_rooms`, and one `image` live on `Property`.
- Property detail nests `room_configs` and `rooms`, exposes owner phone/WhatsApp, and appends `related_properties` in the view.
- APIs alternate between raw arrays and envelopes such as `{success, data, count}`.
- Money is inconsistently serialized: property list forces numeric price while most dashboard/payment values are strings.
- IDs are integer database keys. No stable public slug/UUID contract exists.
- Filters are PG-oriented and there are no category routes `/pg`, `/apartments`, `/villas`, or `/office`.
- No pagination, ordering contract, API schema, or declared version prefix is implemented despite comments referring to “API v1”.

## 4. Current authentication and authorization architecture

- Custom `User` extends `AbstractUser`; phone is unique but username remains inherited and login uses phone/password.
- OTP state and identity/KYC media are stored directly on `User`. OTP has no expiry, attempt counter, hashing, or rate-limiting model.
- DRF TokenAuthentication and SessionAuthentication are enabled.
- `User.role` is one of owner/staff/tenant/seeker and drives helper methods. Registration overwrites it, so roles are mutually exclusive.
- Django `is_staff`, `is_superuser`, groups, and permissions still exist but are not integrated with business scoping.
- Global DRF permission is `AllowAny`. Only selected owner/seeker views use `IsAuthenticated`; there is no owner-role check or object-level membership permission.
- Even authenticated owner endpoints generally scope through `property__owner=request.user`, which excludes managers/accountants and cannot express delegated access.
- Many CRUD endpoints expose all organizations' data without authentication or scope validation.
- A tenant can submit a maintenance ticket for an arbitrary property because the posted property is not checked against their active stay.

## 5. Current property ownership model

`Property.owner -> User` is the only ownership mechanism. Owner organization name and payout details are columns on the user. This supports one human owning many properties, but not co-ownership, an organization account, managers, staff/accountants, property-level assignments, ownership history, or a user belonging to multiple organizations.

Some owner queries correctly filter by direct owner, while `PropertyManagementView.get()` deliberately returns `Property.objects.all()`. There is no database-level organization partition key.

## 6. Current tenant/property relationship

`Tenant` is both a person/profile and current lease. It optionally has one `User`, one `Property`, and one `Room`; rent, deposit, join date, status, and payment state are stored on that same row. The one-to-one link means a user cannot have independent customer profiles or concurrent/historical tenant records without mutating the same row.

`Booking` duplicates much of the intended tenancy data but does not model occupancy assignments or agreements. `CurrentStayView` selects `.first()` active booking, so multiple active stays are silently ambiguous. Creating a tenant through `AddTenantView` creates a booking explicitly while a `post_save` signal also creates one, producing duplicate upcoming/active bookings.

## 7. Current room and inventory architecture

- `RoomConfiguration` represents an advertised sharing type/capacity/price.
- `Room` represents a physical numbered room but repeats sharing, rent, deposit, and capacity.
- Beds are counts, not records. A specific bed cannot be assigned, blocked, maintained, priced, or audited.
- `occupied_beds` and `available_beds` are manually stored/derived without transactional assignment logic or check constraints.
- There is no generic space hierarchy for apartments, villas, offices, floors, desks, cabins, parking, or future asset types.
- Pricing and availability are embedded in physical models; there is no Listing.

The example “2-sharing room for ₹9,000” cannot be represented independently from the building/room without conflating configuration, inventory, and offer.

## 8. Current payment and document architecture

`Payment` is a transaction directly tied to tenant/property and a free-text month. It has no tenancy, invoice, line item, due date, currency, gateway metadata, refund, allocation, reconciliation, or idempotency key. A successful *created* payment sets the tenant's single `is_paid=True`; failed/refunded/older-month cases cannot be represented accurately.

`Booking`/`Tenant` store deposits, but deposit collection/refund is not ledgered. Payroll and grocery expenses are separate coarse models, and the owner dashboard combines them procedurally.

Documents are scattered fields (`User.identity_*`, `Tenant.id_proof_image`, `GroceryExpense.receipt_image`, payment `receipt_url`, room/property images). There is no document entity, tenancy agreement, version, verification, expiry, access policy, signature state, or polymorphic attachment convention.

## 9. Problems that prevent the target design

### Critical

1. Single-valued user role and no scoped membership/permission model.
2. Direct user ownership instead of organization ownership.
3. Global `AllowAny` plus unscoped CRUD creates cross-customer data exposure and mutation risk.
4. Physical property, marketplace offer, pricing, and availability are conflated.
5. Tenant profile/current stay/history are conflated; no occupancy assignment model.
6. No inventory items, so beds/desks cannot be uniquely assigned or reserved.
7. No invoices/allocations; `is_paid` is not a valid payment ledger.
8. No generalized documents or agreements.

### High

9. Duplicate `RoomConfiguration`/`Room` concepts and denormalized capacity counters.
10. Cross-property foreign-key consistency is not enforced.
11. Staff are not users/memberships and cannot authenticate or hold scoped access.
12. Duplicate booking creation path and non-unique count-based booking IDs.
13. Accidental route aliases, shadowed endpoints, inconsistent envelopes, and no versioning.
14. No enquiries/leads or visit-request models.
15. Notifications and complaints are tenant-only and globally exposed.
16. Property type choices do not match the required canonical set: Office is missing and several legacy values overlap future categories.

### Scale and reliability

17. Nearby search calculates distance in Python over every active property; use geospatial/indexed querying later.
18. Lists are unpaginated and lack stable ordering/filter schemas.
19. Integer IDs and property names in upload paths are weak public/storage identifiers.
20. SQLite is appropriate locally but PostgreSQL should be the production target; database constraints/indexes are sparse.
21. `rating` is an unaudited value on Property with no review source.
22. Hard-coded `property_id=1` was not found in executable code. Comments/examples use it, but the larger problem is optional client-supplied `property_id` with “all records” fallback and no authorization.

## 10. Models that can be retained

“Retain” means preserve the concept and preferably its table/data, not freeze its current fields.

| Model | Recommendation |
|---|---|
| `accounts.User` | Retain as the authentication identity. Deprecate business-role and organization/payout columns after backfill. |
| `property.Location` | Retain initially; normalize address/geospatial fields over time. Consider renaming to `Locality` to distinguish it from an address. |
| `property.Property` | Retain as the canonical physical asset and migrate its ownership/presentation fields. |
| `rooms.Room` | Retain data by migrating rows into generic `Unit`; optionally keep a proxy/compatibility serializer temporarily. |
| `maintenance.MaintenanceTicket` | Retain concept and records; re-key to tenancy/unit/inventory and organization scope. |
| `visitor.Visitor` | Retain concept and records; improve host/occupancy relation and access control. |
| `grocery.GroceryExpense` | Retain as an operational expense initially, then generalize to `Expense` if non-PG categories require it. |
| `payments.Notification` | Retain data/concept but change recipient to User and add organization/context links. |

## 11. Models that need modification

| Model | Required modification |
|---|---|
| `User` | Treat as identity only; add customer profile if needed; move organization and payout data out; retain legacy `role` read-only during transition. |
| `Property` | Add organization, stable public ID/slug, lifecycle status, timezone/currency, structured address; remove listing price/rating/availability and JSON amenities after backfill. |
| `Location` | Add country/postal hierarchy or replace duplicated property city/state with structured address fields. |
| `Room` -> `Unit` | Generic type/code/floor/parent/capacity/attributes; uniqueness per property; remove rent and mutable occupancy counters. |
| `MaintenanceTicket` | Scope by organization/property; link requester User and optional tenancy/unit/inventory; replace room text; add audit/status events and attachments. |
| `Visitor` | Link host occupancy/tenancy/user; unit optional; add invited/check-in actor and organization scope. |
| `Notification` | Recipient User, channel/template/data/delivery/read timestamps; organization context. |
| `GroceryExpense` | Add organization, creator, property optionality, approval/payment/document relations. |

## 12. Models that should be replaced

| Existing model | Replacement |
|---|---|
| `RoomConfiguration` | `Listing` + `ListingTarget` (unit type/unit/inventory class) + pricing + availability. |
| `Tenant` | `CustomerProfile` (optional) plus `Tenancy` and `OccupancyAssignment`; reuse `User` for identity/contact. |
| `Booking` | `Tenancy` for executed/upcoming stays; optionally `Reservation` before conversion to tenancy. |
| `Payment` | `Invoice`, `InvoiceLine`, `PaymentTransaction`, and `PaymentAllocation` (with optional deposit ledger). |
| `Staff` | `OrganizationMembership` for access identity plus optional `EmployeeProfile`/`Employment` for HR/payroll fields. |
| `Complaint` | A general `SupportCase` or fold property issues into `MaintenanceRequest`; do not keep it inside the payments domain. |

Replacement should be additive first. Legacy rows remain until backfill, dual-read validation, and compatibility retirement are complete.

## 13. New models required

### Identity and organizations

- `Organization(id, public_id, name, legal_name, status, default_currency, timezone, created_at)`
- `OrganizationMembership(organization, user, role, status, joined_at, invited_by)` with roles owner/manager/staff/accountant and unique active membership per user/organization.
- `PropertyAccess(membership, property, role_override?, permissions?)` only when a membership is limited to selected properties. Absence can mean organization-wide access according to role policy.
- `OrganizationPayoutAccount` for UPI/bank/provider details; encrypt/tokenize sensitive fields.
- Optional `EmployeeProfile`/`Employment` for salary and HR data, separate from authorization.

### Property, spaces, and inventory

- `PropertyMedia(property, file, media_type, caption, sort_order, is_primary)`
- `Amenity(id, code, name, category)` and `PropertyAmenity(property, amenity, value/details)`
- `PropertyDocument(property, document)` or a generic document link
- `PGDetails(property one-to-one, gender_policy, meal_policy, curfew, ...)`
- `ApartmentDetails(property one-to-one, configuration/building fields, ...)`
- `VillaDetails(property one-to-one, configuration fields, ...)`
- `OfficeDetails(property one-to-one, office/commercial fields, ...)`
- `Unit(property, parent_unit nullable, code, unit_type, floor, capacity, area, attributes, status)` for room, apartment unit, villa portion, cabin, desk zone, etc.
- `InventoryItem(property, unit, item_type, code, status, attributes)` for bed, desk, parking slot, locker, or equipment when individual assignment matters.

Category detail tables should hold stable/queryable category-specific fields. A bounded `attributes` JSON field may hold experimental long-tail attributes, but must not replace relational fields used for filtering, authorization, pricing, or integrity.

### Marketplace

- `Listing(organization, property, public_id/slug, category, title, description, status, published_at, ...)`
- `ListingTarget(listing, unit nullable, inventory_item nullable, target_type/occupancy_type, quantity)` or equivalent explicit offer target.
- `ListingMedia`, if listing-specific ordering/copy differs from property media.
- `PricePlan(listing, amount, currency, billing_cycle, deposit, effective_from/to, minimum_stay, ...)`
- `Availability(listing, unit/inventory optional, starts_at, ends_at, quantity, status)`; use derived occupancy plus explicit blocks, not a single boolean.
- Optional `ListingAmenity` only for offer-specific amenities/restrictions.

### CRM and visits

- `Lead(organization, user/contact, source, status, assigned_membership, created_at)`
- `Enquiry(lead, listing, message, status, created_at)`
- `VisitRequest(enquiry/lead, property, listing, requested_slot, scheduled_slot, status, assigned_member)`
- `VisitEvent` or status history for rescheduling/audit.

### Tenancy and occupancy

- `Tenancy(organization, property, primary_tenant User, listing/reservation optional, start_date, end_date, status, rent, deposit, billing_cycle, notice dates, created_by)`
- `TenancyParty(tenancy, user, party_role)` for co-tenants, guarantors, occupants, and billing contacts.
- `OccupancyAssignment(tenancy, unit, inventory_item nullable, starts_at, ends_at, status)`; supports room/bed moves without rewriting tenancy history.
- Optional `Reservation` for temporary holds and pre-tenancy booking workflow.
- `TenancyDocument(tenancy, document, document_role)`.

### Billing and documents

- `Invoice(organization, tenancy, number, period_start/end, issue/due dates, currency, status, totals)`
- `InvoiceLine(invoice, type, description, quantity, unit_amount, tax, total, source_ref)`
- `PaymentTransaction(organization, payer, amount, currency, method, provider, provider_reference, status, received_at, idempotency_key)`
- `PaymentAllocation(payment, invoice/invoice_line, amount)`
- `CreditNote`/`Refund` when required; `DepositLedgerEntry` for deposit liability/collection/deduction/refund.
- `Document(organization, uploaded_by, file/storage_key, type, title, status, checksum, issued/expires_at, metadata)`
- Explicit link tables such as `PropertyDocument`, `TenancyDocument`, and `UserDocument`; avoid an unconstrained generic foreign key for core integrity.

### Operations and platform

- `MaintenanceRequest` plus `MaintenanceEvent/Comment/Assignment` and document links.
- `VisitorVisit` linked to host/occupancy and check-in/out actors.
- `Notification` plus `NotificationDelivery` for email/SMS/push attempts.
- `AuditEvent` for permission, financial, tenancy, and status changes.

## 14. Recommended relationships

```text
User ───< OrganizationMembership >─── Organization ───< Property
                     │                         │              │
                     └──< PropertyAccess >─────┘              ├── 0..1 PGDetails
                                                            ├── 0..1 ApartmentDetails
                                                            ├── 0..1 VillaDetails
                                                            ├── 0..1 OfficeDetails
                                                            ├──< PropertyMedia
                                                            ├──< PropertyAmenity >── Amenity
                                                            ├──< PropertyDocument >── Document
                                                            └──< Unit (self-parent hierarchy)
                                                                     └──< InventoryItem

Organization ───< Listing >─── Property
                    │  ├──< ListingTarget >── Unit / InventoryItem
                    │  ├──< PricePlan
                    │  ├──< Availability
                    │  └──< Enquiry >── Lead >── User/contact
                    │                         └──< VisitRequest
                    │
User ───< TenancyParty >─── Tenancy >─── Property
              primary ───────┘  │
                                ├──< OccupancyAssignment >── Unit
                                │                         └── InventoryItem (optional)
                                ├──< TenancyDocument >── Document
                                └──< Invoice ───< InvoiceLine
                                           └──< PaymentAllocation >── PaymentTransaction

User/Member ───< MaintenanceRequest >── Property / Unit / InventoryItem / Tenancy
User/Occupancy ───< VisitorVisit >────── Property / Unit
User ───< Notification ───< NotificationDelivery
```

Key cardinality and constraint rules:

- A property belongs to exactly one organization at a time; ownership transfers should be recorded separately rather than rewriting history invisibly.
- A user can have many memberships and many simultaneous functional roles across organizations.
- Membership roles are organization-scoped; property access can narrow them.
- A listing belongs to one property and may target one or more units/inventory pools. A property can have many listings.
- An occupancy assignment must reference a unit belonging to the tenancy property; inventory, if set, must belong to that unit.
- Prevent overlapping active assignments for exclusive inventory with a PostgreSQL exclusion constraint or transactional equivalent.
- Financial records carry organization and tenancy scope and are immutable after posting; corrections use reversals/credits.

## 15. Recommended permissions architecture

Use role-based defaults plus object scope, not a role string alone.

1. **Platform layer:** Django `is_superuser`/a dedicated platform-admin permission for internal administration. Never infer platform admin from organization membership.
2. **Organization layer:** `OrganizationMembership` assigns owner, manager, staff, or accountant. A user may hold roles in multiple organizations.
3. **Property scope:** `PropertyAccess` limits a membership to an allowed subset. Owners normally have all-organization scope; managers/staff/accountants may be all-property or selected-property.
4. **Action policy:** define named permissions such as `property.view`, `property.manage`, `listing.publish`, `tenancy.manage`, `billing.view`, `billing.collect`, `maintenance.assign`, and `staff.manage`. Map role templates to these permissions; permit explicit grants only if a real use case requires them.
5. **Resource queryset scope:** every private queryset starts from an access service such as `properties_accessible_to(user)` or `for_membership(membership)`. Never fetch globally and check after serialization.
6. **Object checks:** validate organization, property, unit, inventory, and tenancy lineage on writes. Do not trust a posted `property_id`.
7. **Customer access:** tenants see only tenancies for which they are a party and associated invoices/documents/requests. Public users see published listings only.
8. **Audit:** log membership, permission, payout, invoice, payment, and tenancy state changes.

Suggested role defaults:

| Role | Default scope/capabilities |
|---|---|
| Organization owner | Full organization administration, properties, members, listings, operations, billing/payout visibility. |
| Manager | Assigned/all properties; property/listing/tenancy/operations management; no ownership transfer or payout credential changes by default. |
| Staff | Assigned properties; limited operational workflows such as visits, visitors, and maintenance; no financial administration by default. |
| Accountant | Assigned/all properties; invoices, payments, expenses, reports; read-only property/tenancy context; no occupancy or member administration by default. |
| Tenant/customer | Own profile and tenancy-scoped portal actions only. |
| Platform admin | Cross-organization internal administration via separate guarded interfaces. |

Make `IsAuthenticated` the global default. Mark public marketplace/auth endpoints `AllowAny` explicitly. Add integration tests proving cross-organization reads and writes return 404/403.

## 16. Recommended API structure

Introduce `/api/v2/`; keep legacy paths temporarily as `/api/v1/` or existing aliases.

```text
/api/v2/auth/...
/api/v2/me/
/api/v2/me/memberships/

/api/v2/organizations/
/api/v2/organizations/{org_id}/memberships/
/api/v2/organizations/{org_id}/properties/
/api/v2/organizations/{org_id}/properties/{property_id}/units/
/api/v2/organizations/{org_id}/properties/{property_id}/inventory/
/api/v2/organizations/{org_id}/listings/
/api/v2/organizations/{org_id}/leads/
/api/v2/organizations/{org_id}/visit-requests/
/api/v2/organizations/{org_id}/tenancies/
/api/v2/organizations/{org_id}/invoices/
/api/v2/organizations/{org_id}/payments/
/api/v2/organizations/{org_id}/documents/
/api/v2/organizations/{org_id}/maintenance-requests/
/api/v2/organizations/{org_id}/visitor-visits/
/api/v2/organizations/{org_id}/staff/

/api/v2/marketplace/pg/
/api/v2/marketplace/apartments/
/api/v2/marketplace/villas/
/api/v2/marketplace/office/
/api/v2/marketplace/listings/{slug}/
/api/v2/marketplace/listings/{slug}/enquiries/
/api/v2/marketplace/listings/{slug}/visit-requests/

/api/v2/portal/tenancies/
/api/v2/portal/tenancies/{id}/invoices/
/api/v2/portal/tenancies/{id}/payments/
/api/v2/portal/tenancies/{id}/documents/
/api/v2/portal/tenancies/{id}/maintenance-requests/
```

The four public category paths are filtered projections over the common listing/property tables, not separate applications. Each endpoint can accept category-specific filters validated by a category filter set. Common filters include locality, price, availability, furnishing, and amenities; PG adds sharing/gender/meals, apartment/villa add bedrooms/furnishing, and office adds area/workstations/fit-out.

Contract standards:

- Stable public UUID/ULID and slug; do not expose sequential IDs as the only identifier.
- Consistent pagination and envelope (`data`, `meta`, `links`, `errors`).
- Decimal money as strings plus ISO currency.
- ISO-8601 dates/times and explicit property timezone.
- Idempotency keys on financial and reservation creation.
- OpenAPI schema, filter definitions, error codes, and deprecation headers.
- Use nested organization/property routes for discoverability, but authorize from membership rather than trusting nesting alone.

## 17. Proposed Django app/domain structure

Keep one deployment and one database with domain-owned models/services:

```text
config/                 # settings, root URLs, ASGI/WSGI
identity/               # User, customer profile, authentication/KYC
organizations/          # Organization, memberships, property access, role policy
properties/             # Property, address/location, details, units, inventory, amenities/media
marketplace/            # Listing, pricing, availability, enquiries/leads, visit requests
tenancies/              # Reservation, tenancy, parties, occupancy assignments
billing/                # Invoices, lines, payments, allocations, deposits, expenses
documents/              # Document storage/metadata and domain link models
maintenance/            # Requests, assignments, events/comments
visitors/               # Invitations and visit/check-in logs
workforce/              # Optional employee/HR records; authorization stays in organizations
notifications/          # In-app/email/SMS notifications and delivery state
audit/                  # append-only audit events
api/                    # v1 compatibility and v2 routers/serializers
```

Domain rules belong in explicit service/use-case functions with transactions, not serializers or `post_save` side effects. Apps may use foreign keys across domain boundaries in this modular monolith, but cyclic imports should be avoided with string references and service interfaces. Do not split into microservices.

## 18. Database migration strategy

Use an expand/backfill/switch/contract sequence with production-like backups and rehearsal.

1. **Baseline and safety:** reconcile migrations with each deployed database; add data-quality reports for orphan/cross-property references and duplicate bookings. Move production to PostgreSQL first if it still uses SQLite. Freeze and document current API behavior.
2. **Expand identity/business:** add organizations, memberships, access scopes, payout accounts, and nullable `Property.organization`. Create one organization per legacy owner; copy `organization_name`/payout details; create owner membership; attach every property.
3. **Expand assets:** add property detail/media/amenity/document tables, units, inventory. Backfill `Room -> Unit`, generate bed inventory where trustworthy, and record discrepancies instead of inventing occupancy assignments.
4. **Expand marketplace:** add listings/prices/availability. Convert each active property/room configuration into draft listings, with explicit mapping rules per property type. Keep old property price/amenity/image fields as read compatibility sources.
5. **Expand tenancy:** add tenancy/party/assignment tables. Map legacy tenant+booking rows, deduplicate signal-created bookings, and derive assignments only where property/room lineage is valid. Preserve original IDs in migration reference fields.
6. **Expand billing/documents:** create invoices/lines/transactions/allocations and document metadata. Import payments as transactions; create historical invoices/allocations only when month/property/tenant interpretation is reliable. Flag ambiguous records for reconciliation.
7. **Dual read/write:** v2 writes new tables; compatibility services emit old v1 shapes. For a bounded window, mirror essential legacy columns in the same transaction—not asynchronous signals—and compare results/metrics.
8. **Permission cutover:** change global default to authenticated, deploy scoped query services and object-level tests, then explicitly reopen public listing/auth APIs. This is a security change and should not wait for every data migration.
9. **Switch clients:** release frontend category pages and organization/property selector against v2; remove assumptions about one current stay/property. Track v1 usage.
10. **Contract:** stop legacy writes, archive/reconcile old tables/columns, remove route aliases and shadowed handlers, then remove `User.role`, direct property owner, old tenant/booking, configuration, and payment structures in later migrations.

Every backfill must be restartable, batched, idempotent, measurable, and reversible before the contract phase. Validate row counts, sums of money, active occupancies, capacity, and cross-organization access before cutover.

## 19. Backward compatibility risks

| Risk | Mitigation |
|---|---|
| Frontend expects `user.role` and distinct owner/seeker registration. | Continue emitting a deprecated derived `primary_role`/`roles` bridge; registration creates appropriate membership/profile without erasing other roles. |
| Frontend expects price/availability on Property. | v1 adapter selects a representative published listing; v2 returns listings explicitly. Do not choose silently where multiple offers are ambiguous. |
| Frontend expects `room_configs` and aggregate beds. | Generate compatibility projections from listing targets/inventory; document that counters are derived. |
| Frontend expects one `stay/current`. | Keep endpoint returning a selected/default active tenancy only if unambiguous; otherwise return a documented conflict and move clients to tenancy lists. |
| Existing owner URLs and `property_id` filters. | Preserve read aliases temporarily, enforce scope immediately, add org/property context headers or v2 nesting, and publish deprecation dates. |
| Accidental `/seeker/*` and `/locations/*` aliases may be in use. | Measure access logs before removal; redirect safe GETs or return deprecation headers; never preserve unsafe unauthenticated mutations. |
| Numeric IDs are embedded in clients/bookmarks. | Store legacy IDs and allow v1 lookup while v2 exposes stable public IDs. |
| Payload envelope and decimal type changes. | Version them; add contract tests/fixtures for both v1 and v2. |
| Tenant/booking duplicates and invalid cross-property links. | Run reconciliation reports and manual exception queues before enforcing constraints. |
| Converting counts into bed inventory may fabricate identity. | Generate deterministic bed codes only with owner confirmation; otherwise retain capacity pools until inventory is curated. |
| Payment history cannot always map cleanly to invoices. | Import immutable transactions, mark allocations as migrated/ambiguous, reconcile balances instead of asserting false precision. |
| Tightening permissions can surface hidden client dependence on global data. | Treat this as a required security fix; provide scoped replacement calls, not a compatibility bypass. |
| Media URL/path changes. | Preserve storage keys, introduce document/media redirects, and avoid bulk file moves during schema migration. |

## 20. Recommended implementation phases

### Phase 0 — Stabilize and specify

- Add OpenAPI/contract fixtures and security tests around current behavior.
- Inventory production data and endpoint usage; resolve duplicate/shadowed URLs.
- Fix critical unauthenticated management access with a deliberately coordinated compatibility release.
- Decide canonical status vocabularies, currency/timezone behavior, and stable IDs.

### Phase 1 — Organizations and scoped authorization

- Add Organization, Membership, PropertyAccess, payout account.
- Backfill owners/properties and implement accessible-query services.
- Add organization/property selector contract to dashboard APIs.
- Keep legacy role as a deprecated derived field.

**Exit criterion:** every private operation is authenticated, organization-scoped, and covered by cross-tenant tests.

### Phase 2 — Canonical property, units, and category details

- Add category detail, media, amenities, documents, Unit and InventoryItem.
- Backfill rooms and capacity; add database constraints.
- Adapt owner dashboard by property capabilities/type rather than separate dashboards.

**Exit criterion:** PG, Apartment, Villa, and Office assets share one hierarchy and can be managed under multiple properties per organization.

### Phase 3 — Marketplace

- Add Listing, targets, price plans, availability, media.
- Launch common marketplace service and four category projections/routes.
- Add pagination, indexed filters, publishing workflow, and SEO/public slugs.

**Exit criterion:** one property supports multiple independently priced/available listings.

### Phase 4 — CRM and visit workflow

- Add leads, enquiries, assignments, and visit requests/history.
- Convert enquiries/reservations to tenancy without duplicating identity.

### Phase 5 — Tenancy and occupancy

- Add Tenancy, parties, occupancy assignments, reservations, agreements.
- Backfill/deduplicate Tenant and Booking; implement moves and historical stays.
- Release tenant portal tenancy list/current selection.

**Exit criterion:** a user may have multiple historical/concurrent relationships and specific unit/bed assignments are auditable.

### Phase 6 — Billing, payments, and documents

- Add invoice/line/payment/allocation/deposit ledger and generalized documents.
- Backfill transactions and agreements; integrate idempotent payment flows.
- Replace `is_paid`, free-text month, salary paid flag, and receipt URL shortcuts.

### Phase 7 — Operations consolidation

- Rework maintenance, visitors, workforce, expenses, and notifications around organization/property/tenancy scope.
- Add assignments, audit trails, attachments, and notification delivery records.

### Phase 8 — Compatibility retirement and scale work

- Migrate remaining clients, publish deprecations, and remove legacy aliases/tables/columns.
- Add query/index tuning, geospatial search if needed, caching for public listings, asynchronous jobs for notifications/media, and observability.
- Scale only proven bottlenecks; retain the modular monolith.

## Proposed target schema: concise decision record

The recommended target schema is centered on five independent concerns:

```text
IDENTITY:     User -> OrganizationMembership -> Organization -> PropertyAccess
ASSETS:       Organization -> Property -> Unit -> InventoryItem
MARKETPLACE:  Property -> Listing -> ListingTarget + PricePlan + Availability
OCCUPANCY:    User -> TenancyParty -> Tenancy -> OccupancyAssignment -> Unit/InventoryItem
FINANCE:      Tenancy -> Invoice -> InvoiceLine <- PaymentAllocation -> PaymentTransaction
```

This schema meets the stated requirements without four category silos or microservices. Property is the canonical asset; category detail tables extend it; Listing is the offer; Tenancy is the time-bounded legal/commercial relationship; OccupancyAssignment is the physical placement; OrganizationMembership plus PropertyAccess is the authorization scope.

## Decisions required before implementation

1. Whether a property can transfer between organizations and whether ownership history must be first-class from day one.
2. Whether shared inventory starts with individually numbered beds/desks or supports capacity pools until operators curate inventory.
3. Whether `Booking` represents a pre-contract reservation in the product; if yes, retain the concept as `Reservation`, separate from `Tenancy`.
4. Whether one membership can hold multiple organization roles simultaneously. The schema should allow it if the business expects owner+accountant combinations; otherwise a single role per membership with explicit permission grants is simpler.
5. Which legacy URL aliases are used by the actual frontend, since frontend source and access logs were unavailable in this repository.

No implementation should begin until these decisions, the v2 contract, migration exception policy, and permission matrix are accepted.
