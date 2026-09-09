import { useRef, useState } from "react";

import {
  SUPPORTED_FILE_ACCEPT,
  SUPPORTED_FILE_EXTENSIONS,
} from "../../utils/constants";

import { formatBytes } from "../../utils/formatters";

const MAX_FILES = 20;

function getExtension(filename) {
  const idx = filename.lastIndexOf(".");

  return idx >= 0
    ? filename.slice(idx).toLowerCase()
    : "";
}

function validateFiles(files) {
  if (!files || files.length === 0) {
    return "Please choose at least one file.";
  }

  if (files.length > MAX_FILES) {
    return `You can upload at most ${MAX_FILES} files at once.`;
  }

  for (const file of files) {
    if (file.size <= 0) {
      return `${file.name} is empty.`;
    }

    const ext = getExtension(
      file.name
    );

    if (
      !SUPPORTED_FILE_EXTENSIONS.includes(
        ext
      )
    ) {
      return (
        `Unsupported file type "${ext || "unknown"}" ` +
        `for ${file.name}. ` +
        `Supported: ${SUPPORTED_FILE_EXTENSIONS.join(
          ", "
        )}`
      );
    }
  }

  return "";
}

export default function FileUpload({
  onUpload,
  uploading,
  progress,
}) {
  const inputRef = useRef(null);

  const [files, setFiles] =
    useState([]);

  const [fieldError, setFieldError] =
    useState("");

  const handleSelect = (event) => {
    const selectedFiles = Array.from(
      event.target.files || []
    );

    const error =
      validateFiles(
        selectedFiles
      );

    setFieldError(error);

    setFiles(
      error
        ? []
        : selectedFiles
    );
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    if (uploading) {
      return;
    }

    const error =
      validateFiles(files);

    if (error) {
      setFieldError(error);
      return;
    }

    onUpload(files);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="card space-y-4"
    >
      <div>
        <label
          className="label"
          htmlFor="file-input"
        >
          Select customer data files
        </label>

        <input
          id="file-input"
          ref={inputRef}
          type="file"
          multiple
          accept={SUPPORTED_FILE_ACCEPT}
          onChange={handleSelect}
          disabled={uploading}
          className={`input ${
            fieldError
              ? "input-error"
              : ""
          }`}
        />

        {fieldError && (
          <p className="field-error">
            {fieldError}
          </p>
        )}

        <p className="mt-1 text-xs text-slate-500">
          Upload multiple CSV, JSON, XLSX,
          XML or PDF customer files together.
        </p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">
            Selected files ({files.length})
          </p>

          <div className="rounded-md bg-slate-50 p-3">
            {files.map((file) => (
              <div
                key={`${file.name}-${file.size}-${file.lastModified}`}
                className="flex justify-between border-b border-slate-200 py-2 text-sm last:border-b-0"
              >
                <span className="font-medium text-slate-700">
                  {file.name}
                </span>

                <span className="text-slate-500">
                  {formatBytes(
                    file.size
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {uploading && (
        <div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-2 rounded-full bg-brand-500 transition-all"
              style={{
                width: `${progress || 0}%`,
              }}
            />
          </div>

          <p className="mt-1 text-xs text-slate-500">
            Uploading… {progress || 0}%
          </p>
        </div>
      )}

      <button
        type="submit"
        className="btn-primary"
        disabled={
          uploading ||
          files.length === 0 ||
          !!fieldError
        }
      >
        {uploading
          ? "Uploading..."
          : `Upload ${
              files.length || ""
            } File${
              files.length === 1
                ? ""
                : "s"
            }`}
      </button>
    </form>
  );
}