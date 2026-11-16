import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useAuth } from "./AuthContext";

const OrderContext = createContext(null);

export function OrderProvider({ children }) {
  const { user, token } = useAuth();
  const [orders, setOrders] = useState([]);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(Boolean(user));
  const sessionRef = useRef(null);
  sessionRef.current = { token, userId: user?.id, role: user?.role };

  const refreshOrders = useCallback(async () => {
    if (!token || user?.role !== "customer") {
      setOrders([]);
      setEvents([]);
      setError("");
      return [];
    }
    const requestToken = token;
    const requestUserId = user.id;
    try {
      const [result, eventResult] = await Promise.all([
        api.bookings(token),
        api.events(token),
      ]);
      if (
        sessionRef.current.token !== requestToken
        || sessionRef.current.userId !== requestUserId
        || sessionRef.current.role !== "customer"
      ) {
        return [];
      }
      setOrders(result);
      setEvents(eventResult);
      setError("");
      return result;
    } catch (requestError) {
      if (
        sessionRef.current.token === requestToken
        && sessionRef.current.userId === requestUserId
        && sessionRef.current.role === "customer"
      ) {
        setError(requestError.message);
      }
      throw requestError;
    }
  }, [token, user]);

  useEffect(() => {
    let active = true;
    if (!user || user.role !== "customer") {
      setOrders([]);
      setEvents([]);
      setError("");
      setLoading(false);
      return undefined;
    }
    setOrders([]);
    setEvents([]);
    setError("");
    setLoading(true);
    Promise.all([api.bookings(token), api.events(token)]).then(([result, eventResult]) => {
      if (active) {
        setOrders(result);
        setEvents(eventResult);
        setError("");
      }
    }).catch((requestError) => {
      if (active) setError(requestError.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [token, user]);

  const cancelOrder = async (id) => {
    await api.updateBookingStatus(token, id, "cancelled");
    await refreshOrders();
  };

  const updateOrderStatus = async (id, status) => {
    await api.updateBookingStatus(token, id, status);
    await refreshOrders();
  };

  return (
    <OrderContext.Provider value={{ orders, events, cancelOrder, updateOrderStatus, refreshOrders, error, loading }}>
      {children}
    </OrderContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useOrders() {
  return useContext(OrderContext);
}
