# Phase 2 property architecture

## Domain

```text
Organization
    ↓
Property
    ├── PGDetails
    ├── ApartmentDetails
    ├── VillaDetails
    ├── OfficeDetails
    │
    ├── PropertyMedia
    ├── PropertyAmenity ── Amenity
    │
    └── Unit
          ↓
      InventoryItem
```

`Property` is the physical asset and has stable types `PG`, `APARTMENT`, `VILLA`, and `OFFICE`. Legacy values remain readable but V2 rejects them for new writes. Structured location, lifecycle, timezone, currency, slug, and public ID are core fields. Legacy `owner`, price, rating, image, JSON amenities, room counters, and gender fields remain compatibility fields and are not V2 sources of truth.

Each category detail table is optional and one-to-one. Model validation requires the matching property type. Type changes are transactional and blocked while any old detail row exists; a future curated workflow can explicitly migrate or archive those facts.

## Units and capacity

Units represent manageable spaces and may form a same-property parent hierarchy. Root codes are unique per property; child codes are unique per parent. Capacity is non-negative physical capacity. A capacity pool requires no inventory rows. Inventory items are optional assignable resources (`BED`, `DESK`, `PARKING_SLOT`, `LOCKER`, `OTHER`), unique by code within a unit, and validated to share the unit's property.

## Media and amenities

`PropertyMedia` supports multiple ordered files with captions and primary markers. If none exist, V2 can expose legacy `Property.image` as a compatibility media item. `Amenity` plus `PropertyAmenity` is canonical; legacy JSON remains untouched. The migration seeds a small vocabulary and maps only exact aliases. Unmapped values are recorded in `LegacyMappingIssue`.

## Legacy migration

Every legacy `Room` becomes a `ROOM` Unit linked by `legacy_room`. Room number, property, capacity, and active state are mapped. Rent, deposit, and occupied beds remain only on Room. No bed identities are fabricated. Duplicate room numbers receive deterministic suffixed Unit codes and a review issue. `RoomConfiguration` remains unchanged because it combines capacity, pricing, and an offer rather than consistently identifying physical space.

Ambiguous legacy property types (`Co-living`, `Rented Building`, `Room`, `Residence`) are not guessed. Exact `Apartment` and `Villa` values are canonicalized. Issues remain queryable in the admin.

## V2 API and security

- `GET/POST /api/v2/organizations/{org_id}/properties/`
- `GET/PATCH /api/v2/organizations/{org_id}/properties/{property_id}/`
- `GET/POST /api/v2/organizations/{org_id}/properties/{property_id}/units/`
- `GET/PATCH /api/v2/organizations/{org_id}/properties/{property_id}/units/{unit_id}/`
- `GET/POST /api/v2/organizations/{org_id}/properties/{property_id}/inventory/`
- `GET/POST /api/v2/organizations/{org_id}/properties/{property_id}/units/{unit_id}/inventory/`

All lookups intersect the URL organization with Phase 1 accessible-property querysets. Reads require `property.view`; writes require `property.manage`. Foreign organization and property identifiers resolve as not found and cannot grant access by themselves.

## Document boundary

No Document model is introduced. Phase 2 has no concrete document behavior, and a placeholder table would couple physical assets prematurely to Phase 6 verification, agreement, and finance semantics. The future boundary is a property-scoped document relation authorized through the same access service.
