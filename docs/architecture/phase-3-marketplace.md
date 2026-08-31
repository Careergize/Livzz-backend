# Phase 3 marketplace architecture

## Property and listing boundaries

`Property` is the physical asset and remains the root of units, inventory, location, category details, amenities, and property media. `Listing` is a separately publishable commercial offer. One property can therefore expose several offers without duplicating or changing its physical hierarchy.

```text
Organization -> Property -> Unit -> InventoryItem
                      |
                      +-> Listing -> ListingTarget
                                  -> PricePlan history
                                  -> Availability records
                                  -> ListingMedia overrides
```

Listing categories are `PG`, `APARTMENT`, `VILLA`, and `OFFICE`; a listing category must equal its property's canonical `property_type`. Marketplace state is owned by Listing (`DRAFT`, `PUBLISHED`, `PAUSED`, `ARCHIVED`) and never inferred from `Property.is_active`.

## Listing targets

Every publishable listing has exactly one target. `PROPERTY` offers the whole property, `UNIT` offers a canonical unit, `INVENTORY_ITEM` offers an explicit bed/desk/item, and `CAPACITY_POOL` offers a positive quantity of capacity from one canonical unit. Model validation and transactional management writes reject targets outside the listing property, which also prevents cross-organization lineage.

## Price plans

PricePlan is the V2 pricing source. It stores amount, ISO-style currency code, billing cycle, deposit, optional maintenance amount, effective interval, minimum stay, and state. Historical and future plans are retained. Active intervals may not overlap; public serialization resolves exactly one plan effective at request time. No current plan means the listing is not returned publicly, and conflicting current plans raise an explicit validation error rather than selecting one silently.

Legacy `Property.price`, `Room.rent`, and `RoomConfiguration.rent` remain compatibility inputs only. Phase 3 creates no invoices, collections, or payments.

## Availability

Availability is interval-based and has `AVAILABLE`, `BLOCKED`, or `UNAVAILABLE` state. A record can refine a listing with an optional same-property unit or inventory item. Quantity is accepted only for capacity-pool listings. Missing records serialize as `null`; legacy occupied-bed counters are not treated as availability. Phase 5 can later reconcile these explicit records with occupancy assignments.

## Media

ListingMedia provides listing-specific ordering/copy and can reference an existing PropertyMedia row without duplicating a physical file. If a listing has no overrides, the public response uses ordered property media and finally the legacy property image as an explicit compatibility fallback. The first item becomes primary only when stored media has no primary marker.

## Publishing lifecycle

`validate_listing_for_publish(listing)` returns structured errors. Publishing requires correct organization/property lineage, matching category, title, one valid target, exactly one effective price, complete stored address/city/state, matching category-detail data, and a usable listing/property media source. `publish` requires `listing.publish`; pause removes a listing from public results immediately. Draft, paused, and archived rows are never exposed publicly.

## APIs and projections

Public anonymous reads:

- `GET /api/v2/marketplace/listings/`
- `GET /api/v2/marketplace/listings/{slug}/`
- `GET /api/v2/marketplace/pg/`
- `GET /api/v2/marketplace/apartments/`
- `GET /api/v2/marketplace/villas/`
- `GET /api/v2/marketplace/office/`

Category routes are filtered projections of the common Listing queryset. Common filters are city, locality, price range, comma-separated canonical amenity codes, current availability, sort, and pagination. Category filters use structured Phase 2 fields: PG gender/meals/sharing; apartment bedrooms/furnishing/preferred tenant/parking; villa bedrooms/furnishing; and office type/lease type/area/workstation capacity. Unsupported claims are not synthesized. `PRICE_LOW`, `PRICE_HIGH`, and `NEWEST` are explicit sorts. `RELEVANCE` is intentionally absent; default ordering is published time descending, created time descending, then ID.

Authenticated organization management:

- `GET/POST /api/v2/organizations/{org_id}/listings/`
- `GET/PATCH /api/v2/organizations/{org_id}/listings/{listing_id}/`
- `POST .../{listing_id}/publish/` and `POST .../{listing_id}/pause/`
- `GET/POST .../{listing_id}/prices/`
- `GET/POST .../{listing_id}/availability/`

All querysets intersect the URL organization with Phase 1 property scope. Reads use `listing.view`, mutations use `listing.manage`, and lifecycle actions use `listing.publish`.

## Public response contract and data truth

The stable resource contains listing identity/title/category, real property identity and stored location, target-derived offer data, current stored pricing, explicit current availability or `null`, canonical amenities, deterministic media, stored category details, and the real publication timestamp. Decimal money is serialized as fixed two-decimal strings.

The API does not emit ratings, reviews, verification, recommendations, distance claims, instant-booking claims, fabricated map points, or inferred availability. Missing legitimate facts remain `null`, empty, or omitted according to the field contract.

## Legacy migration

Migration `0002_conservative_legacy_marketplace` creates only drafts. A positive canonical `Property.price` can seed a property-target draft and monthly plan. A PG RoomConfiguration seeds a capacity-pool draft only when its positive capacity matches exactly one canonical ROOM unit; its rent and deposit seed the plan. Zero/multiple matches and noncanonical sources create a persistent `LegacyMappingIssue`. `Room`, `RoomConfiguration`, and all V1 APIs remain unchanged.

## Query performance

Public reads use `select_related`, `prefetch_related`, and current-price/availability subqueries to avoid per-row asset and marketplace queries. Listing, price interval, availability interval, media ordering, property location/type, and Phase 2 relationship fields have database indexes. All list endpoints are paginated; search engines and caches are deferred.
