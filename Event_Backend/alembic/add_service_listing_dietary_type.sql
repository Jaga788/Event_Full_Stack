ALTER TABLE public.service_listings
ADD COLUMN dietary_type VARCHAR(7);

ALTER TABLE public.service_listings
ADD CONSTRAINT ck_service_listing_dietary_type
CHECK (dietary_type IS NULL OR dietary_type IN ('veg', 'non_veg'));
