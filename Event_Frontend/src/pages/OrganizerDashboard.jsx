import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import DashboardLayout from "../components/DashboardLayout";
import EventConversation from "../components/EventConversation";
import { useAuth } from "../context/AuthContext";
import { formatINR } from "../utils/format";

function OrganizerDashboard() {
  const { user, token } = useAuth();
  const [events, setEvents] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeItem, setActiveItem] = useState("overview");
  const bookingsByEvent = useMemo(() => {
    const grouped = new Map();
    bookings.forEach((booking) => {
      const current = grouped.get(booking.event_id) || [];
      grouped.set(booking.event_id, [...current, booking]);
    });
    return grouped;
  }, [bookings]);

  const refresh = useCallback(async () => {
    const [assignedEvents, assignedBookings] = await Promise.all([
      api.events(token),
      api.bookings(token),
    ]);
    const eventRecords = new Map(assignedEvents.map((event) => [event.id, event]));
    const missingEventIds = [...new Set(
      assignedBookings
        .map((booking) => booking.event_id)
        .filter((eventId) => !eventRecords.has(eventId)),
    )];
    const relatedEvents = await Promise.all(
      missingEventIds.map((eventId) => api.event(token, eventId)),
    );
    relatedEvents.forEach((event) => eventRecords.set(event.id, event));
    const latestBookingAt = new Map();
    assignedBookings.forEach((booking) => {
      const createdAt = Date.parse(booking.created_at || "") || 0;
      latestBookingAt.set(
        booking.event_id,
        Math.max(latestBookingAt.get(booking.event_id) || 0, createdAt),
      );
    });
    const activityAt = (event) => Math.max(
      Date.parse(event.created_at || "") || 0,
      latestBookingAt.get(event.id) || 0,
    );
    setEvents(
      [...eventRecords.values()].sort(
        (left, right) => activityAt(right) - activityAt(left) || right.id - left.id,
      ),
    );
    setBookings(assignedBookings);
    setError("");
  }, [token]);

  useEffect(() => {
    refresh().catch((requestError) => setError(requestError.message));
  }, [refresh]);

  const updateStatus = async (update, message) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await update();
      await refresh();
      setNotice(message);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const eventStatusOptions = (event) => (
    event.status === "confirmed" ? ["completed", "cancelled"] : []
  );
  const bookingStatusOptions = (booking) => (
    booking.status === "confirmed" ? ["completed", "cancelled"] : []
  );
  const navigate = (item) => {
    setActiveItem(item);
    const targetId = {
      overview: "dashboard-overview",
      work: "organizer-work",
      messages: "organizer-messages",
    }[item];
    document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const stats = [
    { label: "Assigned events", value: events.length },
    { label: "Service bookings", value: bookings.length },
  ];

  return (
    <DashboardLayout
      user={user}
      roleLabel="Organizer"
      eyebrow="EVENTORA WORKSPACE"
      title="Your assigned work"
      description="Manage your events and service bookings, and coordinate directly with customers."
      navItems={[
        { id: "overview", label: "Overview" },
        { id: "work", label: "Assigned work", count: events.length + bookings.length },
        { id: "messages", label: "Customer messages", disabled: !events.length },
      ]}
      activeItem={activeItem}
      onNavigate={navigate}
      stats={stats}
    >
      {error && <p className="error admin-alert" role="alert">{error}</p>}
      {notice && <p className="ok-text admin-alert" role="status">{notice}</p>}
      {!events.length && !bookings.length ? (
        <section className="admin-panel" id="organizer-work">
          <p className="empty-text">No work has been assigned to your account yet.</p>
        </section>
      ) : (
        <div className="organizer-work-list" id="organizer-work">
          {events.map((event, index) => {
            const eventBookings = bookingsByEvent.get(event.id) || [];
            return (
              <article className="admin-panel organizer-work-card" key={event.id}>
                <div className="order-header">
                  <div>
                    <p className="eyebrow">EVENT #{event.id}</p>
                    <h2>{event.title}</h2>
                  </div>
                  <span className={`status-badge status-${event.status}`}>{event.status}</span>
                </div>
                <div className="organizer-customer-details">
                  <p><strong>Customer:</strong> {event.customer_name} · {event.customer_email}</p>
                  {event.customer_phone && (
                    <p><strong>Phone:</strong> <a href={`tel:${event.customer_phone}`}>{event.customer_phone}</a></p>
                  )}
                  <p><strong>Event date:</strong> {new Date(event.event_date).toLocaleDateString()}</p>
                  <p><strong>Venue:</strong> {event.venue}</p>
                  <p><strong>Budget:</strong> {event.budget == null ? "Not specified" : formatINR(event.budget)}</p>
                  {event.description && <p><strong>Details:</strong> {event.description}</p>}
                </div>
                {eventStatusOptions(event).length > 0 && (
                  <label className="organizer-status-control">
                    Update event status
                    <select value={event.status} disabled={busy} onChange={(change) => updateStatus(
                      () => api.updateEventStatus(token, event.id, change.target.value),
                      "Event status updated.",
                    )}>
                      <option value={event.status}>{event.status}</option>
                      {eventStatusOptions(event).map((status) => <option key={status} value={status}>{status}</option>)}
                    </select>
                  </label>
                )}
                <section className="order-items">
                  <h3>Service bookings</h3>
                  {eventBookings.length ? eventBookings.map((booking) => (
                    <div className="order-item organizer-booking" key={booking.id}>
                      <div>
                        <strong>{booking.item_title}</strong>
                        <p>{booking.quantity} × {formatINR(booking.unit_price)} · Total {formatINR(booking.total_price)}</p>
                        <p>Booking #{booking.id} · {booking.status}</p>
                      </div>
                      {bookingStatusOptions(booking).length > 0 && (
                        <label>
                          Update status
                          <select value={booking.status} disabled={busy} onChange={(change) => updateStatus(
                            () => api.updateBookingStatus(token, booking.id, change.target.value),
                            "Booking status updated.",
                          )}>
                            <option value={booking.status}>{booking.status}</option>
                            {bookingStatusOptions(booking).map((status) => <option key={status} value={status}>{status}</option>)}
                          </select>
                        </label>
                      )}
                    </div>
                  )) : <p className="muted">No individual service bookings are attached to this event.</p>}
                </section>
                <EventConversation
                  id={index === 0 ? "organizer-messages" : undefined}
                  event={event}
                  bookings={eventBookings}
                />
              </article>
            );
          })}
        </div>
      )}
    </DashboardLayout>
  );
}

export default OrganizerDashboard;
