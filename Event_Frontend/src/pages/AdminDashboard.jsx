import { useCallback, useEffect, useRef, useState } from "react";
import {
  CalendarDays,
  ClipboardList,
  LayoutDashboard,
  Package,
  Tags,
  Users,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { formatDate, formatINR } from "../utils/format";
import DashboardLayout from "../components/DashboardLayout";
import AdminItemEditor from "../components/AdminItemEditor";
import SuccessToast from "../components/SuccessToast";
import useCatalog from "../hooks/useCatalog";
import CategoryThumbnail from "../components/CategoryThumbnail";

const sections = ["Overview", "Users", "Events", "Bookings", "Catalog", "Categories"];
const sectionIcons = {
  Overview: LayoutDashboard,
  Users,
  Events: CalendarDays,
  Bookings: ClipboardList,
  Catalog: Package,
  Categories: Tags,
};
const sectionHeaders = {
  Overview: {
    title: "Admin overview",
    description: "Review activity and monitor your event catalog.",
  },
  Users: {
    title: "User accounts",
    description: "Review registered accounts and manage user roles.",
  },
  Events: {
    title: "Event requests",
    description: "Review event details, update status, and assign organizers.",
  },
  Bookings: {
    title: "Service bookings",
    description: "Manage booking status and organizer assignments.",
  },
  Catalog: {
    title: "Catalog management",
    description: "Create, edit, and manage packages and service listings.",
  },
  Categories: {
    title: "Category management",
    description: "Create, edit, and manage event and service categories.",
  },
};
const bookingStatuses = ["requested", "confirmed", "cancelled", "completed"];
const initialServiceForm = {
  title: "",
  description: "",
  category_id: "",
  price: "",
  price_unit: "per_event",
  image_url: "",
  dietary_type: "",
  event_category_ids: [],
};
const initialPackageForm = {
  title: "",
  description: "",
  price: "",
  price_unit: "per_event",
  image_url: "",
  badge: "",
  max_guests: "",
  included_items: "",
  event_category_ids: [],
};

function AdminDashboard() {
  const { token, user, logout } = useAuth();
  const navigate = useNavigate();
  const { section: sectionParam } = useParams();
  const { refreshCatalog, categories: eventCategories, serviceCategories } = useCatalog();
  const catalogCategories = [...eventCategories, ...serviceCategories];
  const section = sections.find((item) => item.toLowerCase() === sectionParam?.toLowerCase()) || "Overview";
  const [catalogView, setCatalogView] = useState("list");
  const [data, setData] = useState({
    users: [], events: [], bookings: [], categories: [], packages: [], services: [],
  });
  const [categoryForm, setCategoryForm] = useState({ name: "", kind: "event", description: "" });
  const [serviceForm, setServiceForm] = useState(initialServiceForm);
  const [packageForm, setPackageForm] = useState(initialPackageForm);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [imageUploadStatus, setImageUploadStatus] = useState({});
  const [editingItem, setEditingItem] = useState(null);
  const [busy, setBusy] = useState(false);
  const workspaceRef = useRef(null);

  const showSuccessToast = (message) => {
    setToast({ id: Date.now(), message });
  };

  const refresh = useCallback(async () => {
    setError("");
    const [users, events, bookings, categories, packages, services] = await Promise.all([
      api.users(token),
      api.events(token),
      api.bookings(token),
      api.categories("?limit=200"),
      api.packages(),
      api.services(),
    ]);
    setData({ users, events, bookings, categories, packages, services });
  }, [token]);

  useEffect(() => {
    refresh().catch((requestError) => setError(requestError.message));
  }, [refresh]);

  useEffect(() => {
    if (workspaceRef.current) workspaceRef.current.scrollTop = 0;
  }, [section]);

  useEffect(() => {
    if (sectionParam && !sections.some((item) => item.toLowerCase() === sectionParam.toLowerCase())) {
      navigate("/admin/overview", { replace: true });
    }
  }, [navigate, sectionParam]);

  const runAction = async (action, message) => {
    setBusy(true);
    setError("");
    setToast(null);
    try {
      await action();
      await refresh();
      showSuccessToast(message);
      return true;
    } catch (requestError) {
      setError(requestError.message);
      return requestError.message;
    } finally {
      setBusy(false);
    }
  };

  const saveEditedItem = (kind, id, payload) => runAction(async () => {
    if (kind === "category") await api.updateCategory(token, id, payload);
    if (kind === "service") await api.updateServiceListing(token, id, payload);
    if (kind === "package") await api.updatePackage(token, id, payload);
    if (kind === "event") await api.updateEvent(token, id, payload);
    if (["category", "service", "package"].includes(kind)) refreshCatalog();
  }, `${kind[0].toUpperCase()}${kind.slice(1)} updated.`);

  const updateEventStatus = (event, status) => runAction(
    () => api.updateEventStatus(token, event.id, status),
    "Event status updated.",
  );

  const assignEvent = (event, organizerId) => runAction(
    () => api.assignEvent(token, event.id, Number(organizerId)),
    "Event organizer assigned.",
  );

  const assignBooking = (booking, organizerId) => runAction(
    () => api.assignBooking(token, booking.id, Number(organizerId)),
    "Booking organizer assigned.",
  );

  const createCategory = (event) => {
    event.preventDefault();
    runAction(async () => {
      await api.createCategory(token, {
        ...categoryForm,
        name: categoryForm.name.trim(),
        description: categoryForm.description.trim() || null,
      });
      refreshCatalog();
      setCategoryForm({ name: "", kind: "event", description: "" });
    }, "Category created.");
  };

  const createServiceListing = (event) => {
    event.preventDefault();
    runAction(async () => {
      await api.createService(token, {
        title: serviceForm.title.trim(),
        description: serviceForm.description.trim() || null,
        category_id: Number(serviceForm.category_id),
        organizer_id: null,
        event_category_ids: serviceForm.event_category_ids,
        price: Number(serviceForm.price),
        price_unit: serviceForm.price_unit,
        dietary_type: serviceForm.dietary_type || null,
        image_url: serviceForm.image_url.trim() || null,
      });
      setServiceForm(initialServiceForm);
      setImageUploadStatus((current) => ({ ...current, service: null }));
      setCatalogView("list");
      refreshCatalog();
    }, "Service listing created.");
  };

  const uploadCatalogImage = async (event, formType, updateImageUrl) => {
    const fileInput = event.currentTarget;
    const file = event.target.files?.[0];
    if (!file) return;

    setBusy(true);
    setError("");
    setToast(null);
    setImageUploadStatus((current) => ({
      ...current,
      [formType]: { kind: "pending", message: `Uploading ${file.name}…` },
    }));
    try {
      const uploaded = await api.uploadImage(token, file);
      updateImageUrl(uploaded.image_url);
      fileInput.value = "";
      setImageUploadStatus((current) => ({
        ...current,
        [formType]: {
          kind: "success",
          message: `${file.name} uploaded. Publish the listing to save it.`,
        },
      }));
      showSuccessToast("Image uploaded successfully.");
    } catch (requestError) {
      setError(requestError.message);
      fileInput.value = "";
      setImageUploadStatus((current) => ({
        ...current,
        [formType]: { kind: "error", message: requestError.message },
      }));
    } finally {
      setBusy(false);
    }
  };

  const createPackageListing = (event) => {
    event.preventDefault();
    runAction(async () => {
      await api.createPackage(token, {
        title: packageForm.title.trim(),
        description: packageForm.description.trim(),
        organizer_id: null,
        event_category_ids: packageForm.event_category_ids,
        price: Number(packageForm.price),
        price_unit: packageForm.price_unit,
        image_url: packageForm.image_url.trim() || null,
        badge: packageForm.badge.trim() || null,
        max_guests: packageForm.max_guests ? Number(packageForm.max_guests) : null,
        included_items: packageForm.included_items.split("\n").map((item) => item.trim()).filter(Boolean),
      });
      setPackageForm(initialPackageForm);
      setImageUploadStatus((current) => ({ ...current, package: null }));
      setCatalogView("list");
      refreshCatalog();
    }, "Package created.");
  };

  const activeServiceCategories = data.categories.filter(
    (category) => category.kind === "service" && category.is_active,
  );
  const activeEventCategories = data.categories.filter(
    (category) => category.kind === "event" && category.is_active,
  );
  const activeOrganizers = data.users.filter(
    (account) => account.role === "organizer" && account.is_active,
  );
  const selectedServiceCategory = activeServiceCategories.find(
    (category) => category.id === Number(serviceForm.category_id),
  );
  const serviceIsCatering = selectedServiceCategory?.name.trim().toLowerCase() === "catering";
  const toggleServiceEventCategory = (categoryId) => {
    const categoryIds = serviceForm.event_category_ids.includes(categoryId)
      ? serviceForm.event_category_ids.filter((id) => id !== categoryId)
      : [...serviceForm.event_category_ids, categoryId];
    setServiceForm({ ...serviceForm, event_category_ids: categoryIds });
  };
  const togglePackageEventCategory = (categoryId) => {
    const categoryIds = packageForm.event_category_ids.includes(categoryId)
      ? packageForm.event_category_ids.filter((id) => id !== categoryId)
      : [...packageForm.event_category_ids, categoryId];
    setPackageForm({ ...packageForm, event_category_ids: categoryIds });
  };
  const packagesCategoryAvailable = activeServiceCategories.some(
    (category) => category.name.trim().toLowerCase() === "packages",
  );

  const countCards = [
    { label: "Registered users", value: data.users.length },
    { label: "Events", value: data.events.length },
    { label: "Bookings", value: data.bookings.length },
    { label: "Packages", value: data.packages.length },
    { label: "Service listings", value: data.services.length },
    { label: "Categories", value: data.categories.length },
  ];
  const navItems = sections.map((label) => {
    const count = {
      Users: data.users.length,
      Events: data.events.length,
      Bookings: data.bookings.length,
      Catalog: data.packages.length + data.services.length,
      Categories: data.categories.length,
    }[label];
    return { id: label, label, icon: sectionIcons[label], count };
  });
  const activeHeader = sectionHeaders[section];
  const navigateToSection = (nextSection) => {
    navigate(`/admin/${nextSection.toLowerCase()}`);
  };
  const navigateCatalogView = (nextView) => {
    setCatalogView(nextView);
    if (workspaceRef.current) workspaceRef.current.scrollTop = 0;
  };
  const exitAdmin = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <DashboardLayout
      variant="admin"
      user={user}
      roleLabel="Administrator"
      onLogout={exitAdmin}
      eyebrow="EVENTORA CONTROL ROOM"
      title={activeHeader.title}
      description={activeHeader.description}
      navItems={navItems}
      activeItem={section}
      onNavigate={navigateToSection}
      stats={section === "Overview" ? countCards : []}
      workspaceRef={workspaceRef}
    >
      {error && <p className="error admin-alert" role="alert">{error}</p>}
      {toast && (
        <SuccessToast
          key={toast.id}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      {section === "Overview" && (
        <section className="admin-panel">
          <h2>Recent activity</h2>
          <p className="muted">Bookings are requests until confirmed by an administrator. Customers can cancel only requested bookings.</p>
          <div className="admin-activity">
            {data.bookings.slice(0, 5).map((booking) => (
              <div key={booking.id}>
                <span>Booking #{booking.id}<small>{booking.item_title}</small></span>
                <b className={`status ${booking.status}`}>{booking.status}</b>
              </div>
            ))}
            {data.bookings.length === 0 && <p className="empty-text">No bookings to review yet.</p>}
          </div>
        </section>
      )}

      {section === "Users" && (
        <section className="admin-panel">
          <h2>User accounts</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>State</th><th>Joined</th><th>Actions</th></tr></thead>
              <tbody>{data.users.map((account) => (
                <tr key={account.id}>
                  <td>{account.full_name}</td><td>{account.email}</td>
                  <td>
                    <select aria-label={`Role for ${account.full_name}`} value={account.role} disabled={busy || account.id === user.id}
                      onChange={(event) => runAction(
                        () => api.updateUserRole(token, account.id, event.target.value),
                        "User role updated.",
                      )}>
                      {["customer", "organizer", "admin"].map((role) => <option key={role} value={role}>{role}</option>)}
                    </select>
                  </td>
                  <td>{account.is_active ? "Active" : "Inactive"}</td>
                  <td>{formatDate(account.created_at)}</td>
                  <td>
                    {account.id !== user.id && <button className="admin-action-button danger" type="button" disabled={busy}
                      onClick={() => window.confirm(`Delete ${account.full_name}?`) && runAction(
                        () => api.deleteUser(token, account.id),
                        "User deleted.",
                      )}>Delete</button>}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}

      {section === "Events" && (
        <section className="admin-panel">
          <h2>Event requests</h2>
          <p className="muted">Accepting an event confirms its requested service bookings. Declining it also declines its pending bookings.</p>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Event</th><th>Customer</th><th>Contact</th><th>Date / venue</th><th>Budget</th><th>Status</th><th>Organizer</th><th>Details</th></tr></thead>
              <tbody>{data.events.map((event) => (
                <tr key={event.id}>
                  <td>{event.title}<small>Event #{event.id}</small></td>
                  <td>{event.customer_name}<small>{event.customer_email}</small></td>
                  <td>{event.customer_phone ? <a href={`tel:${event.customer_phone}`}>{event.customer_phone}</a> : "—"}</td>
                  <td>{formatDate(event.event_date)}<small>{event.venue}</small></td>
                  <td>{event.budget == null ? "—" : formatINR(event.budget)}</td>
                  <td>
                    {event.status === "planning" ? (
                      <div className="admin-request-actions">
                        <button className="btn btn-small" disabled={busy}
                          onClick={() => updateEventStatus(event, "confirmed")}>Accept</button>
                        <button className="btn btn-small btn-outline" disabled={busy}
                          onClick={() => updateEventStatus(event, "cancelled")}>Decline</button>
                      </div>
                    ) : (
                      <select aria-label={`Status for ${event.title}`} value={event.status} disabled={busy}
                        onChange={(change) => updateEventStatus(event, change.target.value)}>
                        {["confirmed", "cancelled", "completed"].map((status) => <option key={status} value={status}>{status}</option>)}
                      </select>
                    )}
                  </td>
                  <td>
                    <select aria-label={`Organizer for ${event.title}`}
                      value={event.organizer_id || ""}
                      disabled={busy || event.status !== "confirmed" || !activeOrganizers.length}
                      onChange={(change) => change.target.value && assignEvent(event, change.target.value)}>
                      <option value="">{event.organizer_id ? "Choose organizer" : "Unassigned"}</option>
                      {event.organizer_id && !activeOrganizers.some((organizer) => organizer.id === event.organizer_id) && (
                        <option value={event.organizer_id}>Organizer #{event.organizer_id} (inactive)</option>
                      )}
                      {activeOrganizers.map((organizer) => (
                        <option key={organizer.id} value={organizer.id}>{organizer.full_name}</option>
                      ))}
                    </select>
                    {!event.organizer_id && event.status === "planning" && (
                      <small>Accept before assignment</small>
                    )}
                    {!event.organizer_id && ["cancelled", "completed"].includes(event.status) && (
                      <small>Cannot assign a {event.status} event</small>
                    )}
                  </td>
                  <td>
                    <button className="admin-action-button" type="button" disabled={busy}
                      onClick={() => setEditingItem({ kind: "event", item: event })}>
                      Edit details
                    </button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
            {data.events.length === 0 && <p className="empty-text">No events found.</p>}
          </div>
        </section>
      )}

      {section === "Bookings" && (
        <section className="admin-panel">
          <h2>Service booking requests</h2>
          <p className="muted">Accept the related event to confirm its service bookings. You can decline a service booking separately or assign its organizer after confirmation.</p>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Booking</th><th>Event</th><th>Customer</th><th>Total</th><th>Status</th><th>Organizer</th></tr></thead>
              <tbody>{data.bookings.map((booking) => (
                <tr key={booking.id}>
                  <td>#{booking.id}<small>{booking.item_title}</small></td>
                  <td>#{booking.event_id}</td><td>#{booking.customer_id}</td>
                  <td>{formatINR(booking.total_price)}</td>
                  <td>
                    {booking.status === "requested" ? (
                      <div className="admin-request-actions">
                        <button className="btn btn-small btn-outline" disabled={busy} onClick={() => runAction(
                          () => api.updateBookingStatus(token, booking.id, "cancelled"),
                          "Booking declined.",
                        )}>Decline</button>
                        <small>Accept event #{booking.event_id} to confirm</small>
                      </div>
                    ) : (
                      <select aria-label={`Status for booking ${booking.id}`} value={booking.status} disabled={busy}
                        onChange={(event) => runAction(
                          () => api.updateBookingStatus(token, booking.id, event.target.value),
                          "Booking status updated.",
                        )}>
                        {bookingStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                      </select>
                    )}
                  </td>
                  <td>
                    <select aria-label={`Organizer for booking ${booking.id}`}
                      value={booking.organizer_id || ""}
                      disabled={busy || booking.status !== "confirmed" || !activeOrganizers.length}
                      onChange={(change) => change.target.value && assignBooking(booking, change.target.value)}>
                      <option value="">{booking.organizer_id ? "Choose organizer" : "Unassigned"}</option>
                      {booking.organizer_id && !activeOrganizers.some((organizer) => organizer.id === booking.organizer_id) && (
                        <option value={booking.organizer_id}>Organizer #{booking.organizer_id} (inactive)</option>
                      )}
                      {activeOrganizers.map((organizer) => (
                        <option key={organizer.id} value={organizer.id}>{organizer.full_name}</option>
                      ))}
                    </select>
                    {!booking.organizer_id && booking.status === "requested" && (
                      <small>Accept before assignment</small>
                    )}
                    {!booking.organizer_id && ["cancelled", "completed"].includes(booking.status) && (
                      <small>Cannot assign a {booking.status} booking</small>
                    )}
                  </td>
                </tr>
              ))}</tbody>
            </table>
            {data.bookings.length === 0 && <p className="empty-text">No bookings found.</p>}
          </div>
        </section>
      )}

      {section === "Catalog" && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <div>
              <h2>Catalog management</h2>
              <p className="muted">Manage packages and service listings in separate views.</p>
            </div>
            <span className="admin-panel-count">{data.packages.length + data.services.length} listings</span>
          </div>
          <div className="admin-catalog-tabs" role="group" aria-label="Catalog pages">
            <button type="button" className={catalogView === "list" ? "active" : ""}
              aria-pressed={catalogView === "list"} onClick={() => navigateCatalogView("list")}>
              Listings
            </button>
            <button type="button" className={catalogView === "package" ? "active" : ""}
              aria-pressed={catalogView === "package"} onClick={() => navigateCatalogView("package")}>
              Add package
            </button>
            <button type="button" className={catalogView === "service" ? "active" : ""}
              aria-pressed={catalogView === "service"} onClick={() => navigateCatalogView("service")}>
              Add service
            </button>
          </div>
          {catalogView === "package" && (
            <>
          <h3>Add a package</h3>
          <form className="organizer-form" onSubmit={createPackageListing}>
            <label>Package title<input value={packageForm.title} maxLength={150} onChange={(event) => setPackageForm({ ...packageForm, title: event.target.value })} required /></label>
            <label>Description<textarea value={packageForm.description} maxLength={5000} onChange={(event) => setPackageForm({ ...packageForm, description: event.target.value })} required /></label>
            <div className="form-grid">
              <label>Price (₹)<input type="number" min="0" step="0.01" value={packageForm.price} onChange={(event) => setPackageForm({ ...packageForm, price: event.target.value })} required /></label>
              <label>Price unit<select value={packageForm.price_unit} onChange={(event) => setPackageForm({ ...packageForm, price_unit: event.target.value })}>
                <option value="per_event">Per event</option><option value="per_person">Per person</option><option value="per_plate">Per plate</option>
              </select></label>
              <label>Badge (optional)<input maxLength={30} value={packageForm.badge} onChange={(event) => setPackageForm({ ...packageForm, badge: event.target.value })} /></label>
              <label>Maximum guests (optional)<input type="number" min="1" value={packageForm.max_guests} onChange={(event) => setPackageForm({ ...packageForm, max_guests: event.target.value })} /></label>
              <label className="span2">Image URL (optional)<input type="text" maxLength={2048} placeholder="https://example.com/image.jpg" value={packageForm.image_url} onChange={(event) => setPackageForm({ ...packageForm, image_url: event.target.value })} /></label>
              <label className="span2">Or upload an image<input type="file" accept="image/jpeg,image/png,image/gif,image/webp" disabled={busy} onChange={(event) => uploadCatalogImage(event, "package", (imageUrl) => setPackageForm((current) => ({ ...current, image_url: imageUrl })))} /></label>
              {imageUploadStatus.package && (
                <p className={`span2 image-upload-status ${imageUploadStatus.package.kind}`} role={imageUploadStatus.package.kind === "error" ? "alert" : "status"}>
                  {imageUploadStatus.package.message}
                </p>
              )}
              {packageForm.image_url && (
                <img
                  className="catalog-image-preview"
                  src={packageForm.image_url}
                  alt="Package image preview"
                  onError={() => setImageUploadStatus((current) => ({
                    ...current,
                    package: { kind: "error", message: "The image URL is set, but its preview could not load. Check the URL or upload server." },
                  }))}
                />
              )}
              <label className="span2">Included items (one per line)<textarea value={packageForm.included_items} onChange={(event) => setPackageForm({ ...packageForm, included_items: event.target.value })} /></label>
            </div>
            <fieldset className="organizer-category-options">
              <legend>Available for event types</legend>
              {activeEventCategories.map((category) => (
                <label key={category.id}>
                  <input type="checkbox" checked={packageForm.event_category_ids.includes(category.id)}
                    onChange={() => togglePackageEventCategory(category.id)} />
                  {category.name}
                </label>
              ))}
            </fieldset>
            <button className="btn" type="submit" disabled={busy || !packagesCategoryAvailable}>
              {busy ? "Publishing…" : "Publish package"}
            </button>
            {!packagesCategoryAvailable && <p className="muted">Add an active service category named "Packages" before publishing packages.</p>}
          </form>
            </>
          )}
          {catalogView === "service" && (
            <>
          <h3>Add a service listing</h3>
          <form className="organizer-form" onSubmit={createServiceListing}>
            <label>Service title<input value={serviceForm.title} maxLength={150} onChange={(event) => setServiceForm({ ...serviceForm, title: event.target.value })} required /></label>
            <label>Description<textarea value={serviceForm.description} onChange={(event) => setServiceForm({ ...serviceForm, description: event.target.value })} /></label>
            <div className="form-grid">
              <label>Service category<select value={serviceForm.category_id} onChange={(event) => setServiceForm({ ...serviceForm, category_id: event.target.value, dietary_type: "" })} required>
                <option value="">Choose a category</option>{activeServiceCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </select></label>
              {serviceIsCatering && (
                <label>Food type<select value={serviceForm.dietary_type} onChange={(event) => setServiceForm({ ...serviceForm, dietary_type: event.target.value })} required>
                  <option value="">Choose a food type</option>
                  <option value="veg">Vegetarian</option>
                  <option value="non_veg">Non-vegetarian</option>
                </select></label>
              )}
              <label>Price (₹)<input type="number" min="0" step="0.01" value={serviceForm.price} onChange={(event) => setServiceForm({ ...serviceForm, price: event.target.value })} required /></label>
              <label>Price unit<select value={serviceForm.price_unit} onChange={(event) => setServiceForm({ ...serviceForm, price_unit: event.target.value })}>
                <option value="per_event">Per event</option><option value="per_person">Per person</option><option value="per_plate">Per plate</option>
              </select></label>
              <label>Image URL (optional)<input type="text" maxLength={2048} placeholder="https://example.com/image.jpg" value={serviceForm.image_url} onChange={(event) => setServiceForm({ ...serviceForm, image_url: event.target.value })} /></label>
              <label>Or upload an image<input type="file" accept="image/jpeg,image/png,image/gif,image/webp" disabled={busy} onChange={(event) => uploadCatalogImage(event, "service", (imageUrl) => setServiceForm((current) => ({ ...current, image_url: imageUrl })))} /></label>
              {imageUploadStatus.service && (
                <p className={`image-upload-status ${imageUploadStatus.service.kind}`} role={imageUploadStatus.service.kind === "error" ? "alert" : "status"}>
                  {imageUploadStatus.service.message}
                </p>
              )}
              {serviceForm.image_url && (
                <img
                  className="catalog-image-preview"
                  src={serviceForm.image_url}
                  alt="Service image preview"
                  onError={() => setImageUploadStatus((current) => ({
                    ...current,
                    service: { kind: "error", message: "The image URL is set, but its preview could not load. Check the URL or upload server." },
                  }))}
                />
              )}
            </div>
            <fieldset className="organizer-category-options">
              <legend>Available for event types</legend>
              {activeEventCategories.map((category) => (
                <label key={category.id}>
                  <input type="checkbox" checked={serviceForm.event_category_ids.includes(category.id)}
                    onChange={() => toggleServiceEventCategory(category.id)} />
                  {category.name}
                </label>
              ))}
            </fieldset>
            <button className="btn" type="submit" disabled={busy || !activeServiceCategories.length}>
              {busy ? "Publishing…" : "Publish service"}
            </button>
          </form>
            </>
          )}
          {catalogView === "list" && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Listing</th><th>Type</th><th>Category</th><th>Food type</th><th>Catalog owner</th><th>Price</th><th>State</th><th>Actions</th></tr></thead>
              <tbody>
                {[
                  ...data.packages.map((item) => ({ ...item, itemType: "package" })),
                  ...data.services.map((item) => ({ ...item, itemType: "service" })),
                ].map((item) => (
                  <tr key={`${item.itemType}-${item.id}`}>
                    <td>{item.title}<small>#{item.id}</small></td>
                    <td>{item.itemType}</td>
                    <td>{item.itemType === "service" ? data.categories.find((category) => category.id === item.category_id)?.name || "—" : "—"}</td>
                    <td>{item.dietary_type === "veg" ? "Vegetarian" : item.dietary_type === "non_veg" ? "Non-vegetarian" : "—"}</td>
                    <td>{item.organizer_id ? data.users.find((account) => account.id === item.organizer_id)?.full_name || `#${item.organizer_id}` : "Admin catalog"}</td>
                    <td>{formatINR(item.price)}<small>{item.price_unit.replaceAll("_", " ")}</small></td>
                    <td>{item.is_active ? "Active" : "Inactive"}</td>
                    <td>
                      <div className="admin-row-actions">
                        <button className="admin-action-button" type="button" disabled={busy}
                          onClick={() => setEditingItem({ kind: item.itemType, item })}>
                          Edit
                        </button>
                        <button className="admin-action-button" type="button" disabled={busy} onClick={() => runAction(
                          () => item.itemType === "package"
                            ? api.updatePackage(token, item.id, {
                              title: item.title, description: item.description,
                              organizer_id: item.organizer_id, event_category_ids: item.event_category_ids,
                              price: item.price, price_unit: item.price_unit, image_url: item.image_url,
                              badge: item.badge, max_guests: item.max_guests, included_items: item.included_items,
                              average_rating: item.average_rating, review_count: item.review_count,
                              is_active: !item.is_active,
                            })
                            : api.updateServiceListing(token, item.id, {
                              title: item.title, description: item.description,
                              category_id: item.category_id, event_category_ids: item.event_category_ids,
                              organizer_id: item.organizer_id, price: item.price, price_unit: item.price_unit,
                              dietary_type: item.dietary_type, image_url: item.image_url, is_active: !item.is_active,
                            }),
                          `Listing ${item.is_active ? "deactivated" : "activated"}.`,
                        )}>{item.is_active ? "Deactivate" : "Activate"}</button>
                        <button className="admin-action-button danger" type="button" disabled={busy} onClick={() => window.confirm(`Delete "${item.title}"?`) && runAction(
                          () => item.itemType === "package"
                            ? api.deletePackage(token, item.id)
                            : api.deleteServiceListing(token, item.id),
                          "Listing deleted.",
                        )}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.packages.length && !data.services.length && <p className="empty-text">No catalog listings found.</p>}
          </div>
          )}
        </section>
      )}

      {section === "Categories" && (
        <section className="admin-panel">
          <h2>Catalog categories</h2>
          <form className="admin-category-form" onSubmit={createCategory}>
            <label>Category name<input value={categoryForm.name} maxLength={100} onChange={(event) => setCategoryForm({ ...categoryForm, name: event.target.value })} required /></label>
            <label>Category type<select value={categoryForm.kind} onChange={(event) => setCategoryForm({ ...categoryForm, kind: event.target.value })}>
              <option value="event">Event</option><option value="service">Service</option>
            </select></label>
            <label>Description<input value={categoryForm.description} maxLength={500} onChange={(event) => setCategoryForm({ ...categoryForm, description: event.target.value })} /></label>
            <button className="btn" type="submit" disabled={busy}>Add category</button>
          </form>
          <div className="admin-category-list">
            {data.categories.map((category) => (
              <div key={category.id}>
                <span className="admin-category-name">
                  <CategoryThumbnail
                    category={catalogCategories.find((item) => item.id === category.id) || category}
                  />
                  <span>{category.name}<small>{category.kind} · {category.is_active ? "active" : "inactive"}</small></span>
                </span>
                <span className="admin-category-actions">
                  <button className="admin-action-button" type="button" disabled={busy}
                    onClick={() => setEditingItem({ kind: "category", item: category })}>
                    Edit
                  </button>
                <button className="admin-action-button danger" type="button" disabled={busy}
                  onClick={() => window.confirm(`Delete category "${category.name}"?`) && runAction(
                    () => api.deleteCategory(token, category.id),
                    "Category deleted.",
                  )}>Delete</button>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
      {editingItem && (
        <AdminItemEditor
          key={`${editingItem.kind}-${editingItem.item.id}`}
          kind={editingItem.kind}
          item={editingItem.item}
          eventCategories={data.categories.filter((category) => category.kind === "event")}
          serviceCategories={data.categories.filter((category) => category.kind === "service")}
          token={token}
          busy={busy}
          onClose={() => setEditingItem(null)}
          onSave={saveEditedItem}
        />
      )}
    </DashboardLayout>
  );
}

export default AdminDashboard;
