// src/components/BackButton/BackButton.jsx
import { useNavigate } from "react-router-dom";

/**
 * Generic "Back" control. Uses React Router history (navigate(-1)) rather
 * than a hardcoded destination, so it always returns to wherever the user
 * actually came from. Pass `fallback` for the rare case there's no history
 * entry (e.g. the page was opened directly via a bookmarked URL).
 */
export default function BackButton({ label = "Back", fallback = "/dashboard" }) {
  const navigate = useNavigate();

  const handleClick = () => {
    if (window.history.length > 2) {
      navigate(-1);
    } else {
      navigate(fallback);
    }
  };

  return (
    <button type="button" onClick={handleClick} className="btn-secondary mb-4">
      <span aria-hidden="true" className="mr-1">←</span>
      {label}
    </button>
  );
}
