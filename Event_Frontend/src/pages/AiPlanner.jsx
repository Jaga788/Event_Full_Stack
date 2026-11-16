import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import CartItemAction from "../components/CartItemAction";
import { useAuth } from "../context/AuthContext";
import useCatalog from "../hooks/useCatalog";
import { formatINR, tomorrowISO } from "../utils/format";

const initialForm = {
  event_category_id: "",
  event_date: "",
  city: "",
  guest_count: "100",
  budget: "",
  preferences: "",
};

function AiPlanner() {
  const { token } = useAuth();
  const { categories, loading: catalogLoading, error: catalogError } = useCatalog();
  const [form, setForm] = useState(initialForm);
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!form.event_category_id && categories.length) {
      setForm((current) => ({
        ...current,
        event_category_id: String(categories[0].id),
      }));
    }
  }, [categories, form.event_category_id]);

  const update = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setPlan(null);
    setBusy(true);
    try {
      const result = await api.createEventPlan(token, {
        event_category_id: Number(form.event_category_id),
        event_date: form.event_date,
        city: form.city.trim(),
        guest_count: Number(form.guest_count),
        budget: form.budget ? Number(form.budget) : null,
        preferences: form.preferences.trim(),
      });
      setPlan(result);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page narrow">
      <h1 className="page-title">AI Event Planner</h1>
      <p className="section-sub left">
        Share the basics and get a tailored event outline with recommendations from
        Eventora’s active packages and services.
      </p>
      {(error || catalogError) && (
        <p className="error" role="alert">{error || catalogError}</p>
      )}
      <form className="checkout-form" onSubmit={submit}>
        <div className="form-grid">
          <label>Occasion
            <select
              name="event_category_id"
              value={form.event_category_id}
              onChange={update}
              required
              disabled={catalogLoading}
            >
              {categories.map((category) => (
                <option key={category.id} value={category.id}>{category.name}</option>
              ))}
            </select>
          </label>
          <label>Event date
            <input
              type="date"
              name="event_date"
              min={tomorrowISO()}
              value={form.event_date}
              onChange={update}
              required
            />
          </label>
          <label>City
            <input
              name="city"
              value={form.city}
              onChange={update}
              maxLength={120}
              placeholder="e.g. Chennai"
              required
            />
          </label>
          <label>Guest count
            <input
              type="number"
              name="guest_count"
              min="1"
              max="10000"
              value={form.guest_count}
              onChange={update}
              required
            />
          </label>
          <label className="span2">Budget (₹, optional)
            <input
              type="number"
              name="budget"
              min="0"
              step="0.01"
              value={form.budget}
              onChange={update}
              placeholder="e.g. 200000"
            />
          </label>
          <label className="span2">Preferences and priorities
            <textarea
              name="preferences"
              rows="4"
              maxLength={1200}
              value={form.preferences}
              onChange={update}
              placeholder="Theme, food preferences, must-have services…"
            />
          </label>
        </div>
        <p className="hint">
          Your event details, preferences, and relevant catalog information are sent to
          OpenAI to generate suggestions. Don’t include phone numbers, exact addresses,
          or other sensitive information.
        </p>
        <button
          className="btn full"
          type="submit"
          disabled={busy || catalogLoading || categories.length === 0}
        >
          {busy ? "Creating your plan…" : "Create my event plan"}
        </button>
      </form>

      {plan && (
        <section className="section" aria-live="polite">
          <p className="eyebrow">Your event plan</p>
          <h2 className="section-title">{plan.event_category} in {plan.city}</h2>
          <p className="section-sub">
            {plan.summary}
          </p>
          <div className="step">
            <h3>Budget guidance</h3>
            <p>{plan.budget_advice}</p>
            <p>
              Estimated catalog total: <strong>{formatINR(Number(plan.total_estimate))}</strong>
              {plan.within_budget === false && " — above your stated budget"}
              {plan.within_budget === true && " — within your stated budget"}
            </p>
          </div>

          <h3 className="page-title">Suggested timeline</h3>
          <div className="steps">
            {plan.timeline.map((item, index) => (
              <article className="step" key={`${item.time}-${index}`}>
                <span className="step-icon">{item.time}</span>
                <h4>{item.activity}</h4>
                <p>{item.details}</p>
              </article>
            ))}
          </div>

          <h3 className="page-title planner-subtitle">Catalog recommendations</h3>
          {plan.recommendations.length ? (
            <div className="service-grid">
              {plan.recommendations.map((item) => {
                const product = {
                  id: `${item.kind}-${item.item_id}`,
                  packageId: item.kind === "package" ? item.item_id : null,
                  serviceListingId: item.kind === "service" ? item.item_id : null,
                  name: item.title,
                  price: Number(item.unit_price),
                  unit: item.price_unit.replaceAll("_", " "),
                };
                return (
                  <article className="service-card" key={`${item.kind}-${item.item_id}`}>
                    <div className="card-body">
                      <p className="card-sub">{item.kind === "package" ? "Package" : "Service"}</p>
                      <Link to={`/service/${product.id}`}><h3>{item.title}</h3></Link>
                      <p>{item.reason}</p>
                      <p className="price">
                        {formatINR(Number(item.unit_price))}
                        <small> {item.price_unit.replaceAll("_", " ")}</small>
                      </p>
                      <p className="hint">
                        Estimated for {plan.guest_count} guests: {formatINR(Number(item.estimated_total))}
                      </p>
                      <CartItemAction
                        product={product}
                        buttonClassName="btn btn-small"
                        onRequireCustomer={() => true}
                      />
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="empty-text">No active catalog items match this event yet.</p>
          )}
        </section>
      )}
    </div>
  );
}

export default AiPlanner;
