  ALTER TABLE public.events
  ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(20);

  UPDATE public.events
  SET customer_phone = btrim(
      substring(description FROM 'Contact:[[:space:]]*([0-9+() -]{7,20})')
  )
  WHERE customer_phone IS NULL
    AND description ~ 'Contact:[[:space:]]*[0-9+() -]{7,20}';

  ALTER TABLE public.bookings
  ALTER COLUMN organizer_id DROP NOT NULL;

  ALTER TABLE public.packages
  ALTER COLUMN organizer_id DROP NOT NULL;

  ALTER TABLE public.service_listings
  ALTER COLUMN organizer_id DROP NOT NULL;
