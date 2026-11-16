import { useMemo, useState } from "react";
import { useOrders } from "../context/OrderContext";
import { useAuth } from "../context/AuthContext";
import EventConversation from "../components/EventConversation";
import { formatINR } from "../utils/format";

function Orders() {
  const { orders, events, cancelOrder, error, loading } = useOrders();
  const { user } = useAuth();
  const [actionError, setActionError] = useState("");
  const bookingsByEvent = useMemo(() => {
    const grouped = new Map();
    orders.forEach((booking) => {
      const current = grouped.get(booking.event_id) || [];
      grouped.set(booking.event_id, [...current, booking]);
    });
    return grouped;
  }, [orders]);

  const formatDate = (value) => value
    ? new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })
    : "Not scheduled";

  const handleCancel = async (bookingId) => {
    setActionError("");
    try {
      await cancelOrder(bookingId);
    } catch (cancelError) {
      setActionError(cancelError.message);
    }
  };

  if (loading) {
    return (
      <div className="container page-content">
        <h1>My Events & Bookings</h1>
        <p>Loading your event requests…</p>
      </div>
    );
  }

  return (
    <div className="container page-content">
      <h1>My Events & Bookings</h1>
      {error && <div className="error">{error}</div>}
      {actionError && <div className="error" role="alert">{actionError}</div>}
      {!events.length && !orders.length ? (
        <div className="empty-state">
          <h2>No event requests yet</h2>
          <p>Plan an event or book a service to see its progress here.</p>
        </div>
      ) : (
        <div className="orders-list">
          {events.map((event) => {
            const eventBookings = bookingsByEvent.get(event.id) || [];
            return (
              <article className="order-card" key={event.id}>
                <div className="order-header">
                  <div>
                    <h2>{event.title}</h2>
                    <span>Request #{event.id} · Submitted {formatDate(event.created_at)}</span>
                  </div>
                  <span className={`status-badge status-${event.status}`}>{event.status}</span>
                </div>
                <div className="order-details">
                  <p><strong>Event date:</strong> {formatDate(event.event_date)}</p>
                  <p><strong>Venue:</strong> {event.venue || "Not specified"}</p>
                  {event.budget != null && <p><strong>Budget:</strong> {formatINR(event.budget)}</p>}
                  {event.description && <p><strong>Details:</strong> {event.description}</p>}
                  <p><strong>Event organizer:</strong> {event.organizer_id ? `Organizer #${event.organizer_id}` : "Not assigned yet"}</p>
                </div>
                <section className="order-items">
                  <h3>Service bookings</h3>
                  {eventBookings.length ? eventBookings.map((booking) => (
                    <div className="order-item" key={booking.id}>
                      <div>
                        <strong>{booking.item_title}</strong>
                        <p>
                          {booking.quantity} × {formatINR(booking.unit_price)}
                          {" · Total: "}{formatINR(booking.total_price)}
                          {" · "}{booking.status}
                          {" · Organizer: "}{booking.organizer_id ? `#${booking.organizer_id}` : "Not assigned"}
                        </p>
                      </div>
                      {booking.status === "requested" && user?.role === "customer" && (
                        <button className="btn btn-small btn-outline" onClick={() => handleCancel(booking.id)}>
                          Cancel
                        </button>
                      )}
                    </div>
                  )) : <p className="muted">No separate service bookings for this event.</p>}
                </section>
                {user?.role === "customer" && (
                  <EventConversation event={event} bookings={eventBookings} />
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default Orders;
