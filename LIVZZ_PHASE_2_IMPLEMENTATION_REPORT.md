# LIVZZ Phase 2 implementation report

## 1–3. Models and migrations

Created `PGDetails`, `ApartmentDetails`, `VillaDetails`, `OfficeDetails`, `Unit`, `InventoryItem`, `PropertyMedia`, `Amenity`, `PropertyAmenity`, and `LegacyMappingIssue`. Extended Property with slug, lifecycle status, locality, country, postal code, timezone, and currency while retaining all legacy fields. Additive migrations `0005` (schema) and `0006` (conservative data backfill) were added.

## 4–5. Legacy migration and review

Legacy Rooms backfill to linked ROOM Units. Property, room number, capacity, and active state are preserved; rent, deposit, and occupancy remain legacy-only. No InventoryItems are fabricated. Exact Apartment/Villa types and known amenity aliases are normalized. Ambiguous property types, unknown amenities, non-string amenity values, and duplicate room codes create persistent `LegacyMappingIssue` rows for manual review.

## 6–7. API and permissions

Organization-scoped property detail/create/update, Unit list/create/detail/update, and property/unit inventory list/create endpoints were added. Every endpoint authenticates and intersects organization and property identifiers with Phase 1 access services. Owners and authorized managers use the existing `property.view`/`property.manage` permissions; unrelated and unaffiliated users cannot enumerate assets.

## 8–9. Tests and results

Phase 2 tests cover all canonical types, invalid input, category integrity, owner/manager/foreign access, unit hierarchy and duplicates, optional inventory and explicit bed/desk records, type transition safety, and legacy Room retention. Django checks and migration drift checks pass. All 15 discovered repository tests pass. A disposable copy of the existing SQLite database migrated successfully: its one legacy Room produced one linked Unit, and one ambiguous value was recorded for review.

## 10–12. Compatibility and debt

Legacy Property owner/marketplace fields, JSON amenities/image, Room, RoomConfiguration, Tenant, Booking, and Payment remain. Public and dashboard URLs were not removed. Database constraints cannot express cross-table lineage, so Unit parent and Inventory property lineage are enforced by model/service validation and transactions. Existing ambiguous values require review through `LegacyMappingIssue`. A complete generalized Document model is intentionally postponed to avoid Phase 6 coupling.

## 13. Phase 3 preparation

Phase 3 can target Property, Unit, or InventoryItem through explicit ListingTarget records and move pricing/availability out of legacy Property and RoomConfiguration fields. It should consume canonical public IDs and preserve the same organization authorization boundary.
