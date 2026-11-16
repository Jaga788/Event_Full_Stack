import { useState } from "react";
import { Link } from "react-router-dom";

function CategoryCard({ category, to = `/events/${category.slug}` }) {
  const [imageFailed, setImageFailed] = useState(false);
  const [c1, c2] = category.colors;
  return (
    <div className="category-card">
      <Link to={to} className="category-card-link">
        <div className="category-art" style={{ background: `linear-gradient(135deg, ${c1}, ${c2})` }}>
          {!imageFailed && category.image ? (
            <img
              src={category.image}
              alt={category.name}
              loading="lazy"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <span aria-hidden="true">{category.name}</span>
          )}
        </div>
        <h3>{category.name}</h3>
        <p>{category.tagline}</p>
      </Link>
      {category.imageCredit && (
        <a
          className="category-card-credit"
          href={category.imageCreditUrl}
          target="_blank"
          rel="noreferrer"
        >
          Photo: {category.imageCredit}
        </a>
      )}
    </div>
  );
}

export default CategoryCard;
