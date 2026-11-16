import { Routes, Route } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Header from "./components/Header";
import Footer from "./components/Footer";
import ProtectedRoute from "./components/ProtectedRoute";
import ScrollToTop from "./components/ScrollToTop";

import Home from "./pages/Home";
import Services from "./pages/Services";
import CategoryPage from "./pages/CategoryPage";
import ServiceDetails from "./pages/ServiceDetails";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import OrderSuccess from "./pages/OrderSuccess";
import Orders from "./pages/Orders";
import Wishlist from "./pages/Wishlist";
import PlanEvent from "./pages/PlanEvent";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import AdminDashboard from "./pages/AdminDashboard";
import OrganizerDashboard from "./pages/OrganizerDashboard";
import AiPlanner from "./pages/AiPlanner";

function App() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="app">
        <main className="page-content session-checking" role="status">
          Checking your session…
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <ScrollToTop />
      <Header />
      <main className="page-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/services" element={<Services />} />
          <Route path="/events/:slug" element={<CategoryPage />} />
          <Route path="/service/:id" element={<ServiceDetails />} />
          <Route path="/cart" element={<ProtectedRoute role="customer"><Cart /></ProtectedRoute>} />
          <Route path="/wishlist" element={<ProtectedRoute role="customer"><Wishlist /></ProtectedRoute>} />
          <Route path="/plan" element={<ProtectedRoute role="customer"><PlanEvent /></ProtectedRoute>} />
          <Route path="/ai-planner" element={<ProtectedRoute role="customer"><AiPlanner /></ProtectedRoute>} />
          <Route path="/login" element={<Login />} />
          <Route path="/admin" element={<ProtectedRoute role="admin"><AdminDashboard /></ProtectedRoute>} />
          <Route path="/organizer" element={<ProtectedRoute role="organizer"><OrganizerDashboard /></ProtectedRoute>} />
          <Route path="/checkout" element={<ProtectedRoute role="customer"><Checkout /></ProtectedRoute>} />
          <Route path="/order-success/:id" element={<ProtectedRoute role="customer"><OrderSuccess /></ProtectedRoute>} />
          <Route path="/orders" element={<ProtectedRoute role="customer"><Orders /></ProtectedRoute>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;
