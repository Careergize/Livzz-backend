# LIVZZ Phase 3 implementation report

## 1. Models created

Created the dedicated `marketplace` app with Listing, ListingTarget, PricePlan, Availability, and ListingMedia. Listing is the marketplace offer and never replaces Property. Targets support property, unit, inventory item, and unit-backed capacity pool offers with model-level same-property lineage validation.

## 2. Migrations

`marketplace.0001_initial` creates the schema, constraints, and indexes. `marketplace.0002_conservative_legacy_marketplace` performs an additive, draft-only legacy conversion after Phase 2 asset backfill. Migration drift reports no changes.

## 3. Marketplace API endpoints

Added anonymous common listing/detail routes and PG, apartment, villa, and office projections under `/api/v2/marketplace/`. Added organization-scoped listing list/create/detail/update, publish, pause, price-plan, and availability endpoints. The frontend was not modified.

## 4. Listing response contract

Public resources contain listing identity, slug/category/title/description, physical property and stored location, explicit target-derived offer, effective pricing, explicit availability or `null`, canonical amenities, deterministic media, category details, and actual `published_at`. V2 list/data/error envelopes are preserved.

## 5. Filters implemented

Common: city, locality, min/max current price, canonical amenities, availability, pagination, `PRICE_LOW`, `PRICE_HIGH`, and `NEWEST`. Default ordering is deterministic newest-publication ordering; no relevance algorithm is claimed. Structured category filters cover PG gender/sharing/meals, apartment bedrooms/furnishing/preferred tenant/parking, villa bedrooms/furnishing, and office type/lease type/area/workstation capacity.

## 6. Publishing rules

The explicit domain service validates organization/property lineage, category compatibility, title, target, unambiguous effective price, stored location, category-detail row, and usable media. Errors are structured. Only PUBLISHED listings with a current price appear publicly; paused/draft/archived listings do not.

## 7. Legacy data migrated

Positive legacy Property prices on canonical properties seed property-target monthly draft offers. PG RoomConfiguration rows seed monthly capacity-pool draft offers only when capacity maps to exactly one canonical ROOM unit. Legacy IDs and source model metadata are retained in `Listing.legacy_source`. No migrated row is automatically published and no occupied-bed value becomes availability.

## 8. LegacyMappingIssues generated

Ambiguous configuration-to-room mappings (zero or multiple exact capacity candidates), invalid zero capacities, and configurations outside canonical PG properties produce persistent issues. The migration does not guess a target.

## 9. Security integration

Management uses existing `listing.view`, `listing.manage`, and `listing.publish` permissions. URL organization, accessible properties, listing organization, and target lineage are intersected before lookup/write. Unrelated organizations receive not found and cannot enumerate or mutate listings. Public routes expose GET only.

## 10. Tests added

Eleven Phase 3 tests cover all categories; category mismatch; all target shapes; cross-property/organization rejection; current/future/expired and conflicting prices; fixed-decimal serialization; availability quantity and lineage; publishing requirements and lifecycle visibility; public filtering/projections/pagination envelope; owner/manager/foreign security; public mutation denial; and absence of fabricated facts.

## 11. Test results

- Django system check: passed, zero issues
- Migration drift: passed, no changes detected
- Phase 3 suite: 11 passed
- Phase 1/2 and legacy regression subset: 15 passed
- Full repository suite: 26 passed in 46.688 seconds
- Existing development DB copy: migrated successfully; 0 listings auto-created, 0 published, 2 RoomConfiguration rows preserved, and 3 total legacy review issues remained/ were recorded

Validation used a disposable Python 3.11 virtual environment with Django 5.2.17 because the repository's pinned Django 6 target requires Python 3.12+. The application uses APIs compatible with the pinned target.

## 12. Performance and indexes

Public querysets select related property/target/category details, prefetch pricing/availability/media/amenities, and annotate effective pricing/availability filters. Indexes cover listing status/category/property/organization/publication time, price effective intervals, availability intervals/status, and media ordering; Phase 2 already indexes property type/location-scope relationships. Pagination is mandatory and capped at 100 rows.

## 13. Remaining compatibility debt

Legacy Property price/rating/image/JSON amenities and V1 marketplace routes remain. Public media may fall back to the legacy property image, but no legacy rating is exposed. Interval-overlap validation is transactional at the service/model layer; a PostgreSQL exclusion constraint can harden concurrent direct writes later. Category filters intentionally omit fields not represented structurally (for example villa preferred tenant). Media management endpoints are not included yet; property media and admin-backed ListingMedia are available.

## 14. Frontend integration contract

The redesigned frontend should consume `/api/v2/marketplace/listings/` or a category projection, follow the V2 `{data, meta}` envelope, treat availability and optional category facts as nullable, display fixed-string monetary values with their returned currency/cycle, and never derive publication from Property flags. Owner tooling should create the listing/target, add an effective price and optional explicit availability, ensure property category/location/media completeness, then call publish and render returned structured errors.

## 15. Recommended next step

Integrate the future frontend against this contract after staging migration/reconciliation. Keep Phase 4 lead/enquiry/visit work separate from Listing and do not introduce reservation, occupancy, billing, review, recommendation, or search-engine behavior into the marketplace domain.
