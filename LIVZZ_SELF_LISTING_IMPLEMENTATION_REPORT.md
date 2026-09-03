# LIVZZ self-service listing implementation report

## 1. Models created/changed

Added `ListerProfile`, `Listing.lister_profile`, the small `ListingDraft` workflow
record, and a database constraint allowing one primary `ListingMedia` per listing.
The legacy `Property.owner` is nullable so broker/manager listing provenance is not
misrepresented as ownership; canonical organization authorization is unchanged.

## 2. Authentication changes

V2 provides register, login, logout, and current-user endpoints using DRF tokens. Safe
current-user data includes the optional profile but excludes private verification notes
and unrelated organization details. V1 auth remains intact.

## 3. Lister profile architecture

Lister classification is a capability profile, not the legacy mutually exclusive
`User.role`. Users may update business details but never verification state. New
profiles are `UNVERIFIED`.

## 4. Organization provisioning

`ensure_lister_organization` reuses a suitable membership or transactionally creates
one internal organization and owner membership. Repeated drafts reuse it and each draft
property receives an access grant.

## 5. Draft architecture

Only `current_step` is workflow state. Substantive data lives in canonical Property,
category details, Unit, InventoryItem, ListingTarget, Amenity, PricePlan, Availability,
PropertyMedia, and ListingMedia records. Partial data is resumable.

## 6. API endpoints

The endpoint and PATCH contract is documented in
[`docs/architecture/self-service-listing.md`](docs/architecture/self-service-listing.md).

## 7. Media upload/storage

Multi-image uploads use Django's replaceable storage abstraction. Pillow validates real
JPEG/PNG/WEBP content and MIME agreement. Limits are 10 MiB per file and 20 images.
Users may list, order, select one primary, and delete their own listing media.

## 8. Security

Every mutation authenticates. Draft/media lookups scope to `created_by`, while Phase 1
organization/property permissions remain active underneath. Body IDs never grant access.

## 9. Tests

Integration coverage includes authentication, all lister types, blocked self-verification,
organization reuse, all property types, partial resume, targets, media, pricing,
explicit/unknown availability, publish, broker provenance, and cross-user denial.

## 10. Test results

All 39 backend tests pass, including the seven new self-service integration tests.
`manage.py check` reports no issues and migration drift checking reports no changes.

## 11. Compatibility impact

Changes are additive. Existing Phase 1-3 APIs and legacy `User.role`, `Tenant`, pricing,
and image compatibility fields remain. No frontend, tenancy, payment, or review code changed.

## 12. Frontend integration contract

Authenticate, create a profile, create a draft with `property_type`, PATCH sections,
upload multipart `images`, resume via draft GET, and call publish. Field-grouped errors
identify incomplete sections. Coordinates and availability are never inferred.

## 13. Known limitations

Identity review, image transformation/scanning, direct signed uploads, moderation queues,
amenity suggestions, and full space editing within the draft API remain future work.
