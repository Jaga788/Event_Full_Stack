import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LayoutDashboard, MessageSquareText, ClipboardCheck } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import DashboardLayout from "../components/DashboardLayout";
import EventConversation from "../components/EventConversation";
import { useAuth } from "../context/AuthContext";
import { formatINR } from "../utils/format";

function OrganizerDashboard() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const { section: sectionParam } = useParams();
  const [events, setEvents] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const sections = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "assigned-work", label: "Assigned work", icon: ClipboardCheck },
    { id: "messages", label: "Customer messages", icon: MessageSquareText },
  ];
  const activeItem = sections.find((item) => item.id === sectionParam)?.id || "overview";
  const workspaceRef = useRef(null);
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

  useEffect(() => {
    if (workspaceRef.current) workspaceRef.current.scrollTop = 0;
  }, [activeItem]);

  useEffect(() => {
    if (sectionParam && !sections.some((item) => item.id === sectionParam.toLowerCase())) {
      navigate("/organizer/overview", { replace: true });
    }
  }, [navigate, sectionParam]);

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
  const navigateToSection = (item) => {
    navigate(`/organizer/${item}`);
  };
  const exitOrganizer = () => {
    logout();
    navigate("/", { replace: true });
  };
  const stats = [
    { label: "Assigned events", value: events.length },
    { label: "Service bookings", value: bookings.length },
  ];

  const activeHeader = {
    overview: {
      title: "Organizer overview",
      description: "Review your workload and recent customer activity.",
    },
    "assigned-work": {
      title: "Assigned work",
      description: "Manage event details and service booking statuses.",
    },
    messages: {
      title: "Customer messages",
      description: "Communicate directly with customers for your assigned events.",
    },
  }[activeItem];

  return (
    <DashboardLayout
      variant="organizer"
      user={user}
      roleLabel="Organizer"
      onLogout={exitOrganizer}
      eyebrow="JAGA EVENTS WORKSPACE"
      title={activeHeader.title}
      description={activeHeader.description}
      navItems={sections.map((item) => ({
        ...item,
        count: item.id === "assigned-work" ? events.length + bookings.length : undefined,
      }))}
      activeItem={activeItem}
      onNavigate={navigateToSection}
      stats={activeItem === "overview" ? stats : []}
      workspaceRef={workspaceRef}
    >
      {error && <p className="error admin-alert" role="alert">{error}</p>}
      {notice && <p className="ok-text admin-alert" role="status">{notice}</p>}

      {activeItem === "overview" && (
        <section className="admin-panel organizer-overview">
          <div className="organizer-overview-heading">
            <div>
              <h2>Recent activity</h2>
              <p className="muted">Your latest assigned events and service requests.</p>
            </div>
          </div>
          {events.length ? events.slice(0, 5).map((event) => (
            <button
              type="button"
              className="organizer-recent-row"
              key={event.id}
              onClick={() => navigate("/organizer/assigned-work")}
            >
              <span>
                <strong>{event.title}</strong>
                <small>{event.customer_name} · {new Date(event.event_date).toLocaleDateString()}</small>
              </span>
              <span className={`status-badge status-${event.status}`}>{event.status}</span>
            </button>
          )) : (
            <p className="empty-text">No work has been assigned to your account yet.</p>
          )}
        </section>
      )}

      {activeItem === "assigned-work" && (
        <>
          {!events.length && !bookings.length ? (
            <section className="admin-panel">
              <p className="empty-text">No work has been assigned to your account yet.</p>
            </section>
          ) : (
            <div className="organizer-work-list">
              {events.map((event) => {
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
                  </article>
                );
              })}
            </div>
          )}
        </>
      )}

      {activeItem === "messages" && (
        <section className="organizer-messages-list">
          {events.length ? events.map((event) => (
            <article className="admin-panel organizer-message-card" key={event.id}>
              <div className="order-header">
                <div>
                  <p className="eyebrow">EVENT #{event.id}</p>
                  <h2>{event.title}</h2>
                </div>
              </div>
              <EventConversation
                event={event}
                bookings={bookingsByEvent.get(event.id) || []}
              />
            </article>
          )) : (
            <section className="admin-panel">
              <p className="empty-text">Messaging is unavailable until an event is assigned.</p>
            </section>
          )}
        </section>
      )}
    </DashboardLayout>
  );
}

export default OrganizerDashboard;
