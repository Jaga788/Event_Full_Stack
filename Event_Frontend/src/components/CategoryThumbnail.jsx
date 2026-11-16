import { useState } from "react";
import categoryArtwork from "../data/categories";

const slugify = (value) => value.toLowerCase().trim().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function CategoryThumbnail({ category, className = "" }) {
  const [imageFailed, setImageFailed] = useState(false);
  const artwork = categoryArtwork.find((item) =>
    item.slug === category.slug || slugify(item.name) === slugify(category.name),
  );
  const image = category.image || artwork?.image;

  if (image && !imageFailed) {
    return (
      <img
        className={`category-thumbnail ${className}`}
        src={image}
        alt=""
        loading="lazy"
        onError={() => setImageFailed(true)}
      />
    );
  }

  return (
    <span className={`category-thumbnail category-thumbnail-fallback ${className}`} aria-hidden="true">
      {category.emoji || "✨"}
    </span>
  );
}

export default CategoryThumbnail;
