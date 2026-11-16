import { useEffect, useState } from "react";
import { CheckCircle2, X } from "lucide-react";

function SuccessToast({ message, onClose }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setVisible(false), 5000);
    return () => window.clearTimeout(timeoutId);
  }, []);

  if (!visible) return null;

  return (
    <div className="success-toast" role="status" aria-live="polite">
      <CheckCircle2 size={20} aria-hidden="true" />
      <span>{message}</span>
      <button type="button" onClick={onClose} aria-label="Dismiss success message">
        <X size={18} aria-hidden="true" />
      </button>
    </div>
  );
}

export default SuccessToast;
