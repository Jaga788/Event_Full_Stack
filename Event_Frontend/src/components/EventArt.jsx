import { useState } from "react";
import categories from "../data/categories";

function EventArt({ service, className = "" }) {
  const serviceCategory = categories.find((c) => c.slug === service.serviceCategorySlug);
  const eventCategory = categories.find((c) => c.slug === service.category);
  const category = serviceCategory || eventCategory;
  const images = [...new Set([
    service.image,
    serviceCategory?.image,
    eventCategory?.image,
  ].filter(Boolean))];

  return (
    <EventArtContent
      key={`${service.id}-${images.join("|")}`}
      service={service}
      className={className}
      category={category}
      images={images}
    />
  );
}

function EventArtContent({ service, className, category, images }) {
  const [imageIndex, setImageIndex] = useState(0);
  const [c1, c2] = category ? category.colors : ["#52656b", "#9d8064"];
  const image = images[imageIndex];

  if (image) {
    return (
      <div className={`art ${className}`}>
        <img
          src={image}
          alt={`${service.name} event`}
          loading="lazy"
          onError={() => setImageIndex((current) => current + 1)}
        />
      </div>
    );
  }

  return (
    <div
      className={`art art-gradient ${className}`}
      style={{ background: `linear-gradient(135deg, ${c1}, ${c2})` }}
      role="img"
      aria-label={service.name}
    >
      <span className="art-dot art-dot-1" />
      <span className="art-dot art-dot-2" />
      <span className="art-fallback-label">{service.sub || "Event service"}</span>
    </div>
  );
}

export default EventArt;
