# Self-service listing architecture

## Identity and provenance

`User` remains the canonical authenticated person. `ListerProfile` is an optional,
one-to-one business classification (`OWNER`, `BROKER`, or `PROPERTY_MANAGER`) and is
not a global authorization role. Verification starts at `UNVERIFIED`; public APIs do
not expose internal verification notes and users cannot change verification state.

Legacy `Tenant` records remain untouched. A later tenancy phase should associate the
canonical person as `User -> TenancyParty -> Tenancy`, rather than creating a tenant
identity during registration.

Every self-service `Listing` records both `created_by` and the creator's
`lister_profile`. This records who offered the property independently from the
property's operational `organization` and nullable legacy `owner`. Self-service only
populates that compatibility owner for `OWNER` profiles; brokers and managers remain
null because their classification is not evidence of legal or operational ownership.

## Organization provisioning and authorization

`ensure_lister_organization(user)` reuses the user's first active, all-property owner
membership, or transactionally creates an internal organization and owner membership.
Draft creation also grants `PropertyAccess`. The organization can remain invisible in
consumer UI while retaining the Phase 1 authorization boundary.

Self-service queries are additionally scoped to `Listing.created_by`. IDs supplied in
payloads never establish authorization. Existing `user_can`, membership, and property
access services continue to protect the canonical lower-level APIs.

## Draft lifecycle and canonical data

`ListingDraft` only links a canonical `Listing` to a resumable `current_step`.
Property facts, category details, targets, amenities, prices, availability, and media
remain in their Phase 2/3 tables instead of an onboarding JSON blob. Steps are advisory.

Creating a draft requires a lister profile and canonical property type. It creates a
draft `Property`, `Listing`, and property-level `ListingTarget` transactionally. Space
updates may create a canonical `Unit`, optional `InventoryItem`, and replace the target
under normal lineage validation. Category data uses `PGDetails`, `ApartmentDetails`,
`VillaDetails`, or `OfficeDetails`; amenities must be active canonical codes.

Pricing updates create a current `PricePlan`, never `Property.price`. Availability is
optional; omission creates no `Availability` and remains unknown. Publishing calls the
existing `publish_listing` and `validate_listing_for_publish`; errors are grouped by
field. Publication and lister verification remain independent lifecycles.

## Media and storage

Uploads create `PropertyMedia` and attach/order it using `ListingMedia`. Files use
Django's configurable default storage, allowing local development and future object
storage without API changes. Pillow decodes content and requires detected JPEG, PNG,
or WEBP type to match the MIME. Limits are 10 MiB per image and 20 per listing.
Ordering is explicit and a database constraint permits only one listing primary image.
All operations are scoped through the authenticated user's draft.

## API contract

- `POST /api/v2/auth/register/`, `login/`, `logout/`; `GET /api/v2/me/`
- `POST|PATCH /api/v2/me/lister-profile/`
- `POST /api/v2/listing-drafts/`; `GET /api/v2/me/listing-drafts/`
- `GET|PATCH /api/v2/listing-drafts/{draft_id}/`
- `GET|POST|PATCH /api/v2/listing-drafts/{draft_id}/media/`
- `DELETE /api/v2/listing-drafts/{draft_id}/media/{media_id}/`
- `POST /api/v2/listing-drafts/{draft_id}/publish/`
- `GET /api/v2/me/listings/`

Draft PATCH accepts `current_step`, `title`, `description`, `property`, `amenities`,
`space`, `target`, `pricing`, and `availability`. Send `availability: null` to clear it;
omission preserves it. Coordinates remain null unless explicitly supplied.

Advanced fraud controls, content scanning, ownership-document review, moderation
queues, and unknown amenity suggestions are future hooks. Moderation should be inserted
before publish and must not overload verification or publication state.
