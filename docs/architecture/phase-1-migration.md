# Phase 1 migration

## New tables

- `organizations_organization`
- `organizations_organizationmembership`
- `organizations_propertyaccess`
- `organizations_organizationpayoutaccount`
- `organizations_propertyorganizationhistory`

`property_property` gains `public_id` and `organization_id`.

## Legacy mapping and compatibility

The data migration creates one organization for each distinct legacy property owner, using a nonblank `User.organization_name` or the deterministic fallback `Organization for user <id>`. It creates/updates an owner membership, copies legacy payee/UPI details to a private payout record, assigns every property, and creates an initial ownership-history row. Existing `User.role`, payout fields, and `Property.owner` are retained. Public legacy search/detail/location payloads and numeric IDs are unchanged.

The backfill uses `get_or_create`/`update_or_create`, stable owner grouping, and atomic migration execution, making repeated application safe against duplicates. It does not create financial or occupancy history. Properties cannot be orphaned because the legacy owner field is required; unexpected missing-owner rows are preserved for manual review rather than guessed.

## Security changes

DRF is authenticated by default. Authentication and active-property discovery views explicitly opt into anonymous access. Legacy management querysets are scoped through organization/property access, and v2 object lookup returns 404 outside scope.

## Known exceptions

Legacy role and ownership fields are intentionally duplicated during the compatibility window. Payout values are migrated as compatibility data but never exposed by v2 serializers. Database-level encryption for payout credentials is still required before storing full bank credentials; Phase 1 stores only a provider/reference string for that reason.
