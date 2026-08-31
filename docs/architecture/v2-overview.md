# Livzz API v2 architecture

Livzz remains a Django modular monolith. New contracts live below `/api/v2/`; legacy numeric-ID endpoints remain compatibility interfaces.

## Identity and organizations

`accounts.User` remains the identity record. `User.role` is legacy compatibility data and is not an authorization source for v2. A user can have memberships in multiple organizations, and each membership can hold multiple role templates. Organizations carry configurable currency and timezone defaults.

## Permissions and property scope

Authorization is centralized in `organizations.access`. Role templates expand to named permissions such as `property.manage` and `billing.collect`. An active membership either covers all organization properties or is narrowed by explicit `PropertyAccess` rows. Querysets are scoped before object lookup so inaccessible IDs return 404 where appropriate.

## Properties

A property has one current organization and a stable UUID public ID. `Property.owner` remains temporarily for legacy reads. `PropertyOrganizationHistory` supports recording transfers without overwriting prior ownership context; legal transfer workflow is deferred.

## Future boundaries

- Marketplace will expose public published listings and category projections. Phase 1 retains existing active-property discovery only.
- Reservation and tenancy remain separate future domains: reservations are pre-move-in holds; tenancies represent contractual occupancy.
- Billing will own invoices, transactions, and allocations. Phase 1 only moves payout configuration to the organization layer and does not fabricate financial history.

## Response contract

V2 single resources use `{ "data": {} }`; lists use `{ "data": [], "meta": { "count", "page", "page_size" } }`; errors use an `errors` array containing `code`, `field`, and `message`.
# Phase 2 property platform

The V2 domain now uses `Organization -> Property -> Unit -> InventoryItem` as its canonical physical-asset hierarchy. Property access continues to use the Phase 1 membership, named-permission, and property-grant services. Marketplace pricing, availability, occupancy, tenancy, and financial workflows remain deliberately outside this boundary.

See [phase-2-properties.md](phase-2-properties.md) for models, compatibility rules, and endpoints.
