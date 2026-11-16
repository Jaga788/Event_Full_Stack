import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../api";
import categoryArtwork from "../data/categories";

const CatalogContext = createContext(null);

const slugify = (value) => value.toLowerCase().trim().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const unitLabel = (unit) => unit.replaceAll("_", " ");

function mapCategory(category) {
  const slug = slugify(category.name);
  const artwork = categoryArtwork.find((item) =>
    slugify(item.name) === slug || item.slug === slug,
  );
  return {
    ...category,
    backendId: category.id,
    slug,
    emoji: artwork?.emoji || (category.kind === "event" ? "🎉" : "✨"),
    image: artwork?.image || "",
    colors: artwork?.colors || ["#315f72", "#b77f52"],
    tagline: category.description || `Explore ${category.name.toLowerCase()} ideas and services.`,
  };
}

function mapCatalogItem(item, type, categories, serviceCategories) {
  const eventCategoryIds = item.event_category_ids || [];
  const eventCategories = categories.filter((category) => eventCategoryIds.includes(category.id));
  const eventCategory = eventCategories[0];
  const serviceCategory = serviceCategories.find((category) => category.id === item.category_id);
  const title = item.title;
  return {
    id: `${type}-${item.id}`,
    catalogId: item.id,
    packageId: type === "package" ? item.id : null,
    serviceListingId: type === "service" ? item.id : null,
    type,
    name: title,
    sub: type === "package" ? "Packages" : serviceCategory?.name || "Services",
    serviceCategorySlug: serviceCategory
      ? slugify(serviceCategory.name)
      : type === "package" ? slugify("Packages") : "",
    category: eventCategory?.slug || "",
    eventCategories: eventCategories.map((category) => slugify(category.name)),
    eventCategoryIds: eventCategories.map((category) => category.id),
    eventCategoryId: eventCategory?.id || null,
    price: Number(item.price),
    unit: unitLabel(item.price_unit),
    dietaryType: item.dietary_type || null,
    image: item.image_url || "",
    emoji: type === "package" ? "🎉" : "✨",
    desc: item.description || "",
    includes: item.included_items || [],
    tag: item.badge || "",
    guests: item.max_guests ? `Up to ${item.max_guests} guests` : "",
    rating: item.average_rating || 0,
    reviews: item.review_count || 0,
    min: 1,
    step: 1,
  };
}

export function CatalogProvider({ children }) {
  const [catalog, setCatalog] = useState({
    categories: [],
    serviceCategories: [],
    services: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const refreshCatalog = useCallback(() => {
    setRefreshKey((current) => current + 1);
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      api.categories("?kind=event&limit=200"),
      api.categories("?kind=service&limit=200"),
      api.packages(),
      api.services(),
    ]).then(([eventCategories, serviceCategories, packages, listings]) => {
      if (!active) return;
      const categories = eventCategories.filter((item) => item.is_active).map(mapCategory);
      const activeServiceCategories = serviceCategories.filter((item) => item.is_active);
      const mappedServiceCategories = activeServiceCategories.map(mapCategory);
      const services = [
        ...packages.filter((item) => item.is_active).map((item) => mapCatalogItem(item, "package", eventCategories, activeServiceCategories)),
        ...listings.filter((item) => item.is_active).map((item) => mapCatalogItem(item, "service", eventCategories, activeServiceCategories)),
      ];
      setCatalog({ categories, serviceCategories: mappedServiceCategories, services });
      setError("");
    }).catch((requestError) => {
      if (active) setError(requestError.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [refreshKey]);

  return (
    <CatalogContext.Provider value={{ ...catalog, loading, error, refreshCatalog }}>
      {children}
    </CatalogContext.Provider>
  );
}

export default function useCatalog() {
  const catalog = useContext(CatalogContext);
  if (!catalog) throw new Error("useCatalog must be used within a CatalogProvider");
  return catalog;
}
