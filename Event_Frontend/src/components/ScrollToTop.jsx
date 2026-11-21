import { useEffect } from "react";
import { useLocation } from "react-router-dom";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    if (
      pathname === "/admin" || pathname.startsWith("/admin/")
      || pathname === "/organizer" || pathname.startsWith("/organizer/")
    ) return;
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default ScrollToTop;
