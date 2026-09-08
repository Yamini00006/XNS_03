// src/App.jsx
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login/Login";
import Dashboard from "./pages/Dashboard/Dashboard";
import Upload from "./pages/Upload/Upload";
import Processing from "./pages/Processing/Processing";
import DataExplorer from "./pages/DataExplorer/DataExplorer";
import CustomerDetails from "./pages/CustomerDetails/CustomerDetails";
import Chatbot from "./pages/Chatbot/Chatbot";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/processing" element={<Processing />} />
        <Route path="/processing/:jobId" element={<Processing />} />
        <Route path="/data" element={<DataExplorer />} />
        <Route path="/data/:customerId" element={<CustomerDetails />} />
        <Route path="/chatbot" element={<Chatbot />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
