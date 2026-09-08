// src/components/FileUpload/FileUpload.jsx
import { useRef, useState } from "react";
import { SUPPORTED_FILE_ACCEPT, SUPPORTED_FILE_EXTENSIONS } from "../../utils/constants";
import { formatBytes } from "../../utils/formatters";

function getExtension(filename) {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx).toLowerCase() : "";
}

export default function FileUpload({ onUpload, uploading, progress }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [fieldError, setFieldError] = useState("");

  const validate = (candidate) => {
    if (!candidate) return "Please choose a file.";
    if (candidate.size <= 0) return "The selected file is empty.";
    const ext = getExtension(candidate.name);
    if (!SUPPORTED_FILE_EXTENSIONS.includes(ext)) {
      return `Unsupported file type "${ext || "unknown"}". Supported: ${SUPPORTED_FILE_EXTENSIONS.join(", ")}`;
    }
    return "";
  };

  const handleSelect = (e) => {
    const candidate = e.target.files?.[0] || null;
    const err = validate(candidate);
    setFieldError(err);
    setFile(err ? null : candidate);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (uploading) return; // prevent duplicate submissions
    const err = validate(file);
    if (err) {
      setFieldError(err);
      return;
    }
    onUpload(file);
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <div>
        <label className="label" htmlFor="file-input">
          Select a file to upload
        </label>
        <input
          id="file-input"
          ref={inputRef}
          type="file"
          accept={SUPPORTED_FILE_ACCEPT}
          onChange={handleSelect}
          disabled={uploading}
          className={`input ${fieldError ? "input-error" : ""}`}
        />
        {fieldError && <p className="field-error">{fieldError}</p>}
        <p className="mt-1 text-xs text-slate-500">
          Supported formats: CSV, JSON, XLSX, XML, PDF (including scanned PDFs)
        </p>
      </div>

      {file && !fieldError && (
        <div className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          <span className="font-medium">{file.name}</span> — {formatBytes(file.size)}
        </div>
      )}

      {uploading && (
        <div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-2 rounded-full bg-brand-500 transition-all"
              style={{ width: `${progress || 0}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-500">Uploading… {progress || 0}%</p>
        </div>
      )}

      <button type="submit" className="btn-primary" disabled={uploading || !file || !!fieldError}>
        {uploading ? "Uploading..." : "Upload"}
      </button>
    </form>
  );
}
