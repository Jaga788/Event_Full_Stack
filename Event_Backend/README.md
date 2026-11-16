# Event Backend

FastAPI backend project structure for the Event application.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On startup, the app creates missing tables and seeds the event and service categories shown below.
This does not update existing tables. Alembic is not configured yet, so apply schema changes to
an existing Supabase database with a reviewed SQL migration.
For an existing Supabase `users` table, add the role column in the Supabase SQL Editor:

```sql
ALTER TABLE public.users
ADD COLUMN role VARCHAR(9) NOT NULL DEFAULT 'customer'
CHECK (role IN ('admin', 'organizer', 'customer'));
```

To store vegetarian and non-vegetarian service listings, apply
[`alembic/add_service_listing_dietary_type.sql`](./alembic/add_service_listing_dietary_type.sql)
to an existing Supabase database before deploying this version. For the admin-approval and
organizer-assignment workflow, also apply
[`alembic/add_admin_assignment_workflow.sql`](./alembic/add_admin_assignment_workflow.sql).
New Catering listings require a food type, and admins can publish multiple listings in the same
service category.

## Authentication and roles

Set a private JWT signing key in `.env` before starting the API. Generate one locally, then copy
the output into `.env`; do not commit or share the key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```env
JWT_SECRET_KEY=replace_with_your_generated_value
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

The app refuses to start if `JWT_SECRET_KEY` is missing or shorter than 32 characters. Register
users through `POST /users`; new accounts always have the `customer` role. Promote the first
administrator directly in the Supabase SQL Editor (replace the email):

```sql
UPDATE public.users SET role = 'admin' WHERE email = 'admin@example.com';
```

Sign in at `POST /auth/token` using form fields `username` (your email) and `password`. Send the
returned access token as `Authorization: Bearer <token>` on protected requests. `GET /auth/me`
returns the authenticated account and role; the frontend can use that role to select the
Admin/Organizer/Customer dashboard. Administrators can assign roles with
`PATCH /users/{user_id}/role` and a JSON body such as `{"role": "organizer"}`.

Role permissions:

- **Admin:** manage users, roles, categories, catalog listings, all event requests, and all bookings. Admins accept requests, then assign organizers to events and service bookings independently.
- **Organizer:** view only events or service bookings assigned to them, update accepted work through completion or cancellation, message the event customer, and call the customer using the phone link. Organizers cannot create events or manage catalog listings.
- **Customer:** create and view only their own event requests and bookings, browse categories/packages/services, cancel requested bookings, and message organizers assigned to their event or service bookings.
- **Admin communication:** read and send messages in every event conversation.

The database health endpoint is available at `http://127.0.0.1:8000/health/db`.
Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Frontend deployment and CORS

The API allows requests from `https://event-full-stack-sigma.vercel.app`, this project's Vercel
preview deployments, and local Vite development at `http://localhost:5173` by default. To use a
different frontend domain, set `CORS_ORIGINS` in the backend environment (for example, in Render)
to a comma-separated list of exact origins, with no trailing slash:

```env
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
```

Redeploy or restart the backend after changing this setting. Do not use `*` for production origins.

## Events, categories, and service listings

All categories use the `categories` table and have a `kind` of `event` or `service`.
The event categories are Wedding, Engagement, Birthday, Maturity Function, Baby Shower & Naming,
and Corporate & Parties. Service categories include Packages, Decoration, Catering, Photography,
Entertainment, Beauty & Styling, and Invitations & Gifts.

- `GET /categories?kind=event` or `GET /categories?kind=service` — list categories
- `POST /categories`, `GET /categories/{category_id}`, `PUT /categories/{category_id}`,
  `DELETE /categories/{category_id}` — manage categories
- `POST /events`, `GET /events/{event_id}`, `PUT /events/{event_id}`,
  `DELETE /events/{event_id}` — customers create and manage their own event requests; Admins manage all
- `PATCH /events/{event_id}/status` — Admins accept or change event status; assigned Organizers can complete or cancel accepted events
- `PATCH /events/{event_id}/assignment` — Admin-only assignment after the event is accepted
- `GET /events/{event_id}/messages` — read an event's conversation
- `POST /events/{event_id}/messages` — send a message between the customer and assigned organizers; specify `recipient_id` when multiple organizers are assigned
- `PATCH /events/{event_id}/messages/{message_id}/read` — mark a received message as read
- `POST /packages`, `GET /packages/{package_id}`, `PUT /packages/{package_id}`,
  `DELETE /packages/{package_id}` — manage event packages
- `GET /packages?event_category_id=...` — filter packages by event type
- `POST /services`, `GET /services/{listing_id}`, `PUT /services/{listing_id}`,
  `DELETE /services/{listing_id}` — manage marketplace service listings
- `GET /services?category_id=...&event_category_id=...` — filter listings

Packages are listed under the seeded `Packages` service category and include event types, pricing,
an optional badge and image URL, maximum guest count, and included items. Ratings are stored as
package fields until a review feature is implemented.

Admins can upload JPEG, PNG, GIF, or WebP images up to 5 MB with `POST /uploads/images`
(multipart field `file`); the returned `image_url` can be used when creating a package or service.
Uploads are stored under `UPLOAD_DIR` (default `uploads/`) and served from `/uploads/`. Configure
`UPLOAD_DIR` to point to persistent storage when deploying, since a local container filesystem may
be temporary.

## User endpoints

- `POST /users` — create a user
- `GET /users` — list users (`skip` and `limit` support pagination)
- `GET /users/{user_id}` — get one user
- `PUT /users/{user_id}` — update a user's name and email; update the password by including it
- `DELETE /users/{user_id}` — delete a user

`POST /users` is public registration and always creates a customer account. User lists and role
changes are Admin-only; users can view and update their own profile. Passwords are hashed and
never included in API responses.

Customers must authenticate to create or view event requests. New requests start in `planning`;
admins change the status to `confirmed` before assigning an event organizer. Service bookings are
created as `requested`; admins confirm a booking before assigning its organizer. Assignment is
independent for each event and each service booking. Existing organizer assignments and statuses
are preserved by the migration.

Category, package, and service listing writes require the Admin role. Event messages are visible
only to the customer, Admins, and organizers assigned to the event or one of its bookings.
Organizers message the event customer; customers select an assigned organizer as the recipient.

## Cart, favorites, and bookings

These endpoints require a bearer token. Customers manage only their own cart, saved items, and
bookings. Cart and favorites support packages and service listings:

- `GET /cart` — view cart items and the current subtotal
- `POST /cart/items` — add exactly one `package_id` or `service_listing_id`, with an optional quantity
- `PATCH /cart/items/{cart_item_id}` — change quantity
- `DELETE /cart/items/{cart_item_id}` or `DELETE /cart` — remove an item or clear the cart
- `GET /favorites` — list saved packages and services
- `POST /favorites` — save exactly one package or service listing
- `DELETE /favorites/{favorite_id}` — unsave an item
- `POST /bookings/checkout` with `{"event_id": 123}` — create a booking request for each cart item
- `GET /bookings` and `GET /bookings/{booking_id}` — Customers see their own bookings, Organizers see their assigned work, and Admins see all
- `PATCH /bookings/{booking_id}/status` — Customers may cancel their own requested booking; Admins accept/change status, and assigned Organizers can complete or cancel accepted bookings
- `PATCH /bookings/{booking_id}/assignment` — Admin-only assignment after the booking is accepted

Checkout requires an event owned by the signed-in Customer and at least one active cart item.
Per-event items must have quantity `1`; per-plate/per-person items can have larger quantities.
Successful checkout snapshots the current item title and price, creates `requested` bookings, and
clears the cart in one transaction. If checkout fails, the cart is retained. Payment processing
is not implemented yet; creating a booking does not charge the Customer.

## AI event planner

The customer-only `POST /ai/event-plan` endpoint creates an event outline and catalog
recommendations using active packages and services. Set an OpenAI API key in the backend
`.env` file to enable it; the key must stay server-side and must not be committed:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

The endpoint validates every suggested catalog ID against active listings and calculates
estimates from database prices. Availability is not checked by the AI and must be confirmed
separately. Customer-provided event details and preferences are sent to OpenAI to generate
the plan together with relevant catalog details; do not enter sensitive personal information.
