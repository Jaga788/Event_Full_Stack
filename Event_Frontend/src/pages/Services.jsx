import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import useCatalog from "../hooks/useCatalog";
import ServiceBrowser from "../components/ServiceBrowser";

function Services() {
  const { categories, serviceCategories, services, loading, error } = useCatalog();
  const [params, setParams] = useSearchParams();
  const q = (params.get("q") || "").trim();
  const cat = params.get("cat") || "all";
  const serviceCategory = params.get("serviceCategory") || "all";
  const selectedServiceCategory = serviceCategories.find(
    (category) => category.slug === serviceCategory,
  );

  const matches = useMemo(() => {
    const text = q.toLowerCase();
    return services.filter((service) => {
      const dietaryText = service.dietaryType === "veg"
        ? "vegetarian"
        : service.dietaryType === "non_veg" ? "non vegetarian" : "";
      const eventCategories = service.eventCategories?.length
        ? service.eventCategories
        : [service.category];
      return (cat === "all" || eventCategories.includes(cat)) &&
        (serviceCategory === "all" || service.serviceCategorySlug === serviceCategory) &&
        (!text || `${service.name} ${service.sub} ${service.desc} ${service.category} ${dietaryText}`.toLowerCase().includes(text));
    });
  }, [q, cat, serviceCategory, services]);

  const setCat = (value) => {
    const next = new URLSearchParams(params);
    if (value === "all") next.delete("cat");
    else next.set("cat", value);
    next.delete("serviceCategory");
    setParams(next);
  };

  const setServiceCat = (value) => {
    const next = new URLSearchParams(params);
    if (value === "all") next.delete("serviceCategory");
    else next.set("serviceCategory", value);
    next.delete("cat");
    setParams(next);
  };

  return (
    <div className="page">
      <h1 className="page-title">
        {q
          ? `Search results for “${q}”`
          : selectedServiceCategory
            ? `${selectedServiceCategory.name} services`
            : "All Services"}
      </h1>
      {loading && <p className="empty-text" role="status">Loading the latest packages and services…</p>}
      {error && <p className="error" role="alert">Could not load the catalog: {error}</p>}

      <div className="chips">
        <button className={cat === "all" ? "active" : ""} onClick={() => setCat("all")}>All events</button>
        {categories.map((c) => (
          <button key={c.slug} className={cat === c.slug ? "active" : ""} onClick={() => setCat(c.slug)}>
            {c.emoji} {c.name}
          </button>
        ))}
      </div>
      {serviceCategories.length > 0 && (
        <div className="chips" aria-label="Filter by service category">
          <button
            className={serviceCategory === "all" ? "active" : ""}
            onClick={() => setServiceCat("all")}
          >
            All service categories
          </button>
          {serviceCategories.map((category) => (
            <button
              key={category.slug}
              className={serviceCategory === category.slug ? "active" : ""}
              onClick={() => setServiceCat(category.slug)}
            >
              {category.emoji} {category.name}
            </button>
          ))}
        </div>
      )}

      {/* Reset sub-category/sort filters when either category filter or search changes. */}
      {!loading && !error && <ServiceBrowser key={`${cat}-${serviceCategory}-${q}`} services={matches} />}
    </div>
  );
}

export default Services;
