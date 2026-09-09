// src/components/Sidebar/Sidebar.jsx
import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/upload", label: "Upload" },
  { to: "/processing", label: "Processing" },
  { to: "/processing-history", label: "Processing History" },
  { to: "/data", label: "Data Explorer" },
  { to: "/chatbot", label: "Chatbot" },
];

export default function Sidebar() {
  return (
    <nav className="w-52 shrink-0 border-r border-slate-200 bg-white py-4">
      <ul className="space-y-1 px-3">
        {LINKS.map((link) => (
          <li key={link.to}>
            <NavLink
              to={link.to}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {link.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}