# V2 marketplace Azure deployment

## Contract and routes

The root URL configuration mounts `api_v2.urls` at `/api/v2/`. The marketplace
URL group exposes anonymous, read-only list routes for `listings`, `pg`,
`apartments`, `villas`, and `office`, plus slug-only listing detail.

Successful responses consistently use `{ "data": ..., "meta": ... }`. Lists put
the result array in `data`; `meta` contains `count`, `page`, `page_size`, and
`total_pages`. Page size defaults to 20 and is capped at 100.

Public serialization reads only canonical `Listing` records in `PUBLISHED`
state with a currently effective price. It does not expose organization users,
owners, tenants, internal mapping data, or legacy ratings. Coordinates come
only from `Property.latitude` and `Property.longitude`. Missing or invalid
stored coordinates serialize as `null`; no geocoding or fallback is used. V2
property writes reject latitude outside -90..90 and longitude outside
-180..180.

Supported shared filters are `city`, `locality`, `min_price`, `max_price`,
`amenities`, `availability`, `sort`, `page`, and `page_size`. Category routes
also use their real structured fields: PG gender/capacity/meals/minimum stay;
apartment bedrooms/furnishing/preferred tenant/parking; villa
bedrooms/furnishing/parking; and office type/area range/capacity/furnishing/
parking/lease type. The legacy `sharing`, `fit_out`, and exact `area` aliases
remain compatible.

## Database and startup

Phase 2 property migrations `0005`/`0006` and marketplace migrations
`0001`/`0002` must run against the configured `DATABASE_URL`. The migration is
conservative: legacy marketplace candidates become drafts and are never
automatically published. No new migration is required by the endpoint fixes.

Azure App Service uses Linux Python 3.12 and the WSGI application
`smart_pg.wsgi:application`. Production startup must run migrations before
Gunicorn, for example:

```text
python manage.py migrate --noinput && gunicorn smart_pg.wsgi:application --bind 0.0.0.0:8000 --timeout 600
```

The GitHub Actions deployment source is the repository's `main` branch.
Requirements are installed and static files collected during the build.

## CORS and settings

Django/corsheaders is the authoritative CORS layer; Azure App Service CORS
must remain empty. Production sets `CORS_ALLOW_ALL_ORIGINS=False` and provides
`CORS_ALLOWED_ORIGINS` as a comma-separated list containing
`http://localhost:5173`, the exact production Vercel origin, and only explicitly
approved preview origins. `DJANGO_ALLOWED_HOSTS` contains
`livzz-backend.azurewebsites.net`. Secrets and `DATABASE_URL` stay in App
Service settings and are not committed.

## Verification

Before deployment run `manage.py check`, `makemigrations --check`, `migrate`,
the complete test suite, and a WSGI import/startup check. After deployment,
request every documented URL and one real published slug; record status,
content type, envelope, pagination, filters, coordinates, and CORS headers.
