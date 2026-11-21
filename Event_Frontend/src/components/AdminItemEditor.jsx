import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api } from "../api";

const PRICE_UNITS = [
  ["per_event", "Per event"],
  ["per_person", "Per person"],
  ["per_plate", "Per plate"],
];

function toLocalDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

function getInitialValues(kind, item) {
  if (kind === "category") {
    return {
      name: item.name || "",
      description: item.description || "",
      is_active: Boolean(item.is_active),
    };
  }

  if (kind === "service") {
    return {
      title: item.title || "",
      description: item.description || "",
      category_id: String(item.category_id || ""),
      event_category_ids: item.event_category_ids || [],
      price: String(item.price ?? ""),
      price_unit: item.price_unit || "per_event",
      dietary_type: item.dietary_type || "",
      image_url: item.image_url || "",
      is_active: Boolean(item.is_active),
    };
  }

  if (kind === "package") {
    return {
      title: item.title || "",
      description: item.description || "",
      event_category_ids: item.event_category_ids || [],
      price: String(item.price ?? ""),
      price_unit: item.price_unit || "per_event",
      image_url: item.image_url || "",
      badge: item.badge || "",
      max_guests: String(item.max_guests ?? ""),
      included_items: (item.included_items || []).join("\n"),
      average_rating: String(item.average_rating ?? 0),
      review_count: String(item.review_count ?? 0),
      is_active: Boolean(item.is_active),
    };
  }

  return {
    title: item.title || "",
    description: item.description || "",
    category_id: String(item.category_id || ""),
    customer_phone: item.customer_phone || "",
    event_date: toLocalDateTime(item.event_date),
    venue: item.venue || "",
    budget: String(item.budget ?? ""),
  };
}

function AdminItemEditor({
  kind,
  item,
  eventCategories,
  serviceCategories,
  token,
  busy,
  onClose,
  onSave,
}) {
  const [values, setValues] = useState(() => getInitialValues(kind, item));
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const title = kind === "event"
    ? "Edit event"
    : kind === "category"
      ? "Edit category"
      : `Edit ${kind}`;

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !busy && !uploading) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [busy, onClose, uploading]);

  const setField = (event) => {
    const { name, type, checked, value } = event.target;
    setValues((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const setServiceCategory = (event) => {
    setValues((current) => ({
      ...current,
      category_id: event.target.value,
      dietary_type: "",
    }));
  };

  const selectedServiceCategory = serviceCategories.find(
    (category) => category.id === Number(values.category_id),
  );
  const serviceIsCatering = selectedServiceCategory?.name.trim().toLowerCase() === "catering";

  const toggleEventCategory = (categoryId) => {
    setValues((current) => ({
      ...current,
      event_category_ids: current.event_category_ids.includes(categoryId)
        ? current.event_category_ids.filter((id) => id !== categoryId)
        : [...current.event_category_ids, categoryId],
    }));
  };

  const uploadImage = async (event) => {
    const fileInput = event.currentTarget;
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError("");
    try {
      const result = await api.uploadImage(token, file);
      setValues((current) => ({ ...current, image_url: result.image_url }));
    } catch (error) {
      setUploadError(error.message);
    } finally {
      fileInput.value = "";
      setUploading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setUploadError("");
    setSaveError("");

    let payload;
    if (kind === "category") {
      payload = {
        name: values.name.trim(),
        description: values.description.trim() || null,
        is_active: values.is_active,
      };
    } else if (kind === "service") {
      payload = {
        title: values.title.trim(),
        description: values.description.trim() || null,
        category_id: Number(values.category_id),
        event_category_ids: values.event_category_ids,
        organizer_id: item.organizer_id,
        price: Number(values.price),
        price_unit: values.price_unit,
        dietary_type: values.dietary_type || null,
        image_url: values.image_url.trim() || null,
        is_active: values.is_active,
      };
    } else if (kind === "package") {
      payload = {
        title: values.title.trim(),
        description: values.description.trim(),
        organizer_id: item.organizer_id,
        event_category_ids: values.event_category_ids,
        price: Number(values.price),
        price_unit: values.price_unit,
        image_url: values.image_url.trim() || null,
        badge: values.badge.trim() || null,
        max_guests: values.max_guests ? Number(values.max_guests) : null,
        included_items: values.included_items
          .split("\n")
          .map((entry) => entry.trim())
          .filter(Boolean),
        average_rating: Number(values.average_rating),
        review_count: Number(values.review_count),
        is_active: values.is_active,
      };
    } else {
      payload = {
        title: values.title.trim(),
        description: values.description.trim() || null,
        category_id: Number(values.category_id),
        customer_id: item.customer_id,
        organizer_id: item.organizer_id,
        customer_phone: values.customer_phone.trim() || null,
        event_date: new Date(values.event_date).toISOString(),
        venue: values.venue.trim(),
        budget: values.budget === "" ? null : Number(values.budget),
        status: item.status,
      };
    }

    const result = await onSave(kind, item.id, payload);
    if (result === true) onClose();
    else if (typeof result === "string") setSaveError(result);
  };

  return (
    <div
      className="admin-editor-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy && !uploading) onClose();
      }}
    >
      <section
        className="admin-editor"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-editor-title"
      >
        <header className="admin-editor-header">
          <div>
            <p className="eyebrow">ADMIN WORKSPACE · {kind.toUpperCase()}</p>
            <h2 id="admin-editor-title">{title}</h2>
            <p>Update the details below, then save your changes.</p>
          </div>
          <button
            className="admin-icon-button"
            type="button"
            aria-label="Close editor"
            disabled={busy || uploading}
            onClick={onClose}
          >
            <X size={19} />
          </button>
        </header>

        <form className="admin-editor-form" onSubmit={handleSubmit}>
          {kind === "category" && (
            <>
              <div className="admin-editor-grid">
                <label>
                  Category name
                  <input name="name" value={values.name} onChange={setField} maxLength={100} required />
                </label>
                <label>
                  Category type
                  <input value={item.kind === "event" ? "Event" : "Service"} disabled />
                </label>
                <label className="admin-editor-wide">
                  Description
                  <textarea name="description" value={values.description} onChange={setField} maxLength={500} />
                </label>
              </div>
              <label className="admin-checkbox-row">
                <input name="is_active" type="checkbox" checked={values.is_active} onChange={setField} />
                <span><strong>Active category</strong><small>Inactive categories are hidden from customers.</small></span>
              </label>
            </>
          )}

          {(kind === "service" || kind === "package") && (
            <>
              <div className="admin-editor-grid">
                <label>
                  {kind === "package" ? "Package title" : "Service title"}
                  <input name="title" value={values.title} onChange={setField} maxLength={150} required />
                </label>
                <label>
                  Price
                  <span className="admin-input-affix">
                    <span aria-hidden="true">₹</span>
                    <input name="price" type="number" min="0" step="0.01" value={values.price} onChange={setField} required />
                  </span>
                </label>
                <label>
                  Price unit
                  <select name="price_unit" value={values.price_unit} onChange={setField}>
                    {PRICE_UNITS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </label>
                {kind === "service" && (
                  <>
                    <label>
                      Service category
                      <select name="category_id" value={values.category_id} onChange={setServiceCategory} required>
                        <option value="">Choose a category</option>
                        {serviceCategories.map((category) => (
                          <option key={category.id} value={category.id}>
                            {category.name}{category.is_active ? "" : " (inactive)"}
                          </option>
                        ))}
                      </select>
                    </label>
                    {serviceIsCatering && (
                      <label>
                        Food type
                        <select name="dietary_type" value={values.dietary_type} onChange={setField} required>
                          <option value="">Choose a food type</option>
                          <option value="veg">Vegetarian</option>
                          <option value="non_veg">Non-vegetarian</option>
                        </select>
                      </label>
                    )}
                  </>
                )}
                {kind === "package" && (
                  <>
                    <label>
                      Badge
                      <input name="badge" value={values.badge} onChange={setField} maxLength={30} />
                    </label>
                    <label>
                      Maximum guests
                      <input name="max_guests" type="number" min="1" value={values.max_guests} onChange={setField} />
                    </label>
                    <label>
                      Average rating
                      <input name="average_rating" type="number" min="0" max="5" step="0.1" value={values.average_rating} onChange={setField} required />
                    </label>
                    <label>
                      Review count
                      <input name="review_count" type="number" min="0" step="1" value={values.review_count} onChange={setField} required />
                    </label>
                  </>
                )}
                <label className="admin-editor-wide">
                  Description
                  <textarea name="description" value={values.description} onChange={setField} maxLength={5000} required={kind === "package"} />
                </label>
                <label className="admin-editor-wide">
                  Image URL
                  <input name="image_url" type="text" value={values.image_url} onChange={setField} maxLength={2048} placeholder="https://…" />
                </label>
                <label className="admin-editor-wide admin-file-field">
                  Upload a new image
                  <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" onChange={uploadImage} disabled={busy || uploading} />
                  <small>{uploading ? "Uploading image…" : "JPEG, PNG, GIF or WebP. Uploading replaces the image URL above."}</small>
                </label>
                {values.image_url && (
                  <div className="admin-editor-preview">
                    <img src={values.image_url} alt="Current catalog item" />
                    <span>Current image preview</span>
                  </div>
                )}
                {kind === "package" && (
                  <label className="admin-editor-wide">
                    Included items <small>Enter one item per line.</small>
                    <textarea name="included_items" value={values.included_items} onChange={setField} />
                  </label>
                )}
              </div>

              <fieldset className="organizer-category-options admin-editor-categories">
                <legend>Available for event types</legend>
                {eventCategories.map((category) => (
                  <label key={category.id}>
                    <input
                      type="checkbox"
                      checked={values.event_category_ids.includes(category.id)}
                      onChange={() => toggleEventCategory(category.id)}
                    />
                    {category.name}{category.is_active ? "" : " (inactive)"}
                  </label>
                ))}
                {!eventCategories.length && <span className="muted">No event categories available.</span>}
              </fieldset>

              <label className="admin-checkbox-row">
                <input name="is_active" type="checkbox" checked={values.is_active} onChange={setField} />
                <span><strong>Active listing</strong><small>Inactive listings are hidden from customers.</small></span>
              </label>
            </>
          )}

          {kind === "event" && (
            <>
              <div className="admin-editor-grid">
                <label>
                  Event title
                  <input name="title" value={values.title} onChange={setField} maxLength={150} required />
                </label>
                <label>
                  Event type
                  <select name="category_id" value={values.category_id} onChange={setField} required>
                    <option value="">Choose an event type</option>
                    {eventCategories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}{category.is_active ? "" : " (inactive)"}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Date and time
                  <input name="event_date" type="datetime-local" value={values.event_date} onChange={setField} required />
                </label>
                <label>
                  Customer phone
                  <input name="customer_phone" type="tel" value={values.customer_phone} onChange={setField} maxLength={20} />
                </label>
                <label className="admin-editor-wide">
                  Venue
                  <input name="venue" value={values.venue} onChange={setField} maxLength={255} required />
                </label>
                <label>
                  Budget
                  <span className="admin-input-affix">
                    <span aria-hidden="true">₹</span>
                    <input name="budget" type="number" min="0" step="0.01" value={values.budget} onChange={setField} />
                  </span>
                </label>
                <label className="admin-editor-wide">
                  Description
                  <textarea name="description" value={values.description} onChange={setField} />
                </label>
              </div>
              <p className="admin-editor-note">
                Event status and organizer assignment are managed from the event list.
              </p>
            </>
          )}

          {(uploadError || saveError) && (
            <p className="admin-editor-error" role="alert">{uploadError || saveError}</p>
          )}
          <footer className="admin-editor-actions">
            <button className="btn btn-outline" type="button" onClick={onClose} disabled={busy || uploading}>
              Cancel
            </button>
            <button className="btn" type="submit" disabled={busy || uploading}>
              {busy ? "Saving…" : uploading ? "Uploading…" : "Save changes"}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}

export default AdminItemEditor;
