import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

function EventConversation({ event, bookings = [], id }) {
  const { token, user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [recipientId, setRecipientId] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const recipients = useMemo(() => {
    if (user.role === "organizer") {
      return [{ id: event.customer_id, label: event.customer_name }];
    }
    if (user.role === "customer") {
      return [...new Set([
        event.organizer_id,
        ...bookings.map((booking) => booking.organizer_id),
      ].filter(Boolean))].map((id) => ({ id, label: `Organizer #${id}` }));
    }
    return [];
  }, [bookings, event, user.role]);

  useEffect(() => {
    const defaultRecipient = recipients[0]?.id;
    setRecipientId((current) =>
      recipients.some((recipient) => String(recipient.id) === current)
        ? current
        : defaultRecipient ? String(defaultRecipient) : "",
    );
  }, [recipients]);

  useEffect(() => {
    let active = true;
    setError("");
    api.eventMessages(token, event.id).then((result) => {
      if (active) setMessages(result);
    }).catch((requestError) => {
      if (active) setError(requestError.message);
    });
    return () => { active = false; };
  }, [event.id, token]);

  const send = async (formEvent) => {
    formEvent.preventDefault();
    setBusy(true);
    setError("");
    try {
      const message = await api.sendEventMessage(token, event.id, {
        content: content.trim(),
        ...(recipientId ? { recipient_id: Number(recipientId) } : {}),
      });
      setMessages((current) => [...current, message]);
      setContent("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="event-conversation" id={id} aria-label="Event messages">
      <h3>Messages</h3>
      <div className="conversation-messages" role="log" aria-live="polite">
        {messages.map((message) => (
          <article
            className={message.sender_id === user.id ? "conversation-message mine" : "conversation-message"}
            key={message.id}
          >
            <p>{message.content}</p>
            <small>{message.sender_name} · {new Date(message.created_at).toLocaleString()}</small>
          </article>
        ))}
        {!messages.length && <p className="empty-text">No messages yet.</p>}
      </div>
      {recipients.length ? (
        <form className="conversation-form" onSubmit={send}>
          {recipients.length > 1 && (
            <label>
              Send to
              <select value={recipientId} onChange={(event) => setRecipientId(event.target.value)} required>
                {recipients.map((recipient) => (
                  <option key={recipient.id} value={recipient.id}>{recipient.label}</option>
                ))}
              </select>
            </label>
          )}
          <label>
            Message
            <textarea value={content} maxLength={5000} onChange={(event) => setContent(event.target.value)} required />
          </label>
          <button className="btn btn-small" type="submit" disabled={busy || !content.trim()}>
            {busy ? "Sending…" : "Send message"}
          </button>
        </form>
      ) : (
        <p className="muted">Messaging will be available after an organizer is assigned.</p>
      )}
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}

export default EventConversation;
