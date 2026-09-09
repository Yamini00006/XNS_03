import { useState } from "react";
import { useNavigate } from "react-router-dom";

import FileUpload from "../../components/FileUpload/FileUpload";
import ErrorMessage from "../../components/ErrorMessage/ErrorMessage";

import { fileService } from "../../services/fileService";
import { processingService } from "../../services/processingService";

import { formatBytes } from "../../utils/formatters";

export default function Upload() {
  const navigate = useNavigate();

  const [uploading, setUploading] =
    useState(false);

  const [progress, setProgress] =
    useState(0);

  const [uploadedFiles, setUploadedFiles] =
    useState([]);

  const [error, setError] =
    useState(null);

  const [starting, setStarting] =
    useState(false);

  const [attributes, setAttributes] =
    useState([]);

  const [selectedAttributes, setSelectedAttributes] =
    useState([]);

  const [discovering, setDiscovering] =
    useState(false);

  const handleUpload = async (files) => {
    if (uploading) {
      return;
    }

    setError(null);
    setUploading(true);
    setProgress(0);
    setAttributes([]);
    setSelectedAttributes([]);

    try {
      const result =
        await fileService.uploadBatch(
          files,
          setProgress
        );

      const uploaded =
        result.files || [];

      setUploadedFiles(uploaded);

      if (uploaded.length > 0) {
        setDiscovering(true);

        const fileIds =
          uploaded.map(
            (file) => file.id
          );

        const discovered =
          await fileService.discoverAttributes(
            fileIds
          );

        const discoveredAttributes =
          discovered.attributes || [];

        setAttributes(
          discoveredAttributes
        );

        // Select all by default so the existing
        // processing behaviour is preserved.
        setSelectedAttributes(
          discoveredAttributes.map(
            (attribute) => attribute.name
          )
        );
      }
    } catch (err) {
      console.error(err);
      setError(err);
    } finally {
      setDiscovering(false);
      setUploading(false);
    }
  };

  const toggleAttribute = (attributeName) => {
    setSelectedAttributes(
      (current) => {
        if (
          current.includes(attributeName)
        ) {
          return current.filter(
            (name) =>
              name !== attributeName
          );
        }

        return [
          ...current,
          attributeName,
        ];
      }
    );
  };

  const selectAllAttributes = () => {
    setSelectedAttributes(
      attributes.map(
        (attribute) =>
          attribute.name
      )
    );
  };

  const clearAllAttributes = () => {
    setSelectedAttributes([]);
  };

  const handleStartProcessing =
    async () => {
      if (
        starting ||
        uploadedFiles.length === 0
      ) {
        return;
      }

      if (
        attributes.length > 0 &&
        selectedAttributes.length === 0
      ) {
        setError(
          "Please select at least one attribute."
        );
        return;
      }

      setStarting(true);
      setError(null);

      try {
        const fileIds =
          uploadedFiles.map(
            (file) => file.id
          );

        const result =
          await processingService.startBatch(
            fileIds,
            selectedAttributes
          );

        const jobIds =
          result.jobs.map(
            (job) => job.id
          );

        navigate(
          `/processing/batch?job_ids=${jobIds.join(
            ","
          )}`
        );
      } catch (err) {
        console.error(err);
        setError(err);
      } finally {
        setStarting(false);
      }
    };

  return (
    <div className="max-w-2xl space-y-6">

      <h1 className="text-lg font-semibold text-slate-800">
        Upload Customer Data
      </h1>

      <FileUpload
        onUpload={handleUpload}
        uploading={uploading}
        progress={progress}
      />

      {error && (
        <ErrorMessage error={error} />
      )}

      {uploadedFiles.length > 0 && (
        <div className="card space-y-5">

          <div>
            <p className="text-sm font-semibold text-green-700">
              Upload successful.
            </p>

            <p className="mt-1 text-sm text-slate-500">
              {uploadedFiles.length} customer
              data files are ready for
              processing.
            </p>
          </div>

          <div className="space-y-2">
            {uploadedFiles.map(
              (file) => (
                <div
                  key={file.id}
                  className="rounded-md border border-slate-200 p-3"
                >
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">
                      {file.original_name}
                    </span>

                    <span className="text-xs text-slate-500">
                      {formatBytes(
                        file.file_size_bytes
                      )}
                    </span>
                  </div>

                  <p className="mt-1 text-xs uppercase text-slate-400">
                    {file.file_format}
                  </p>
                </div>
              )
            )}
          </div>

          {discovering && (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700">
              Discovering attributes from
              uploaded files...
            </div>
          )}

          {!discovering &&
            attributes.length > 0 && (
              <div className="space-y-4">

                <div>
                  <h2 className="text-sm font-semibold text-slate-800">
                    Select attributes to
                    extract
                  </h2>

                  <p className="mt-1 text-xs text-slate-500">
                    These attributes were
                    discovered from your
                    uploaded files.
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={
                      selectAllAttributes
                    }
                    className="rounded border px-3 py-1 text-xs"
                  >
                    Select All
                  </button>

                  <button
                    type="button"
                    onClick={
                      clearAllAttributes
                    }
                    className="rounded border px-3 py-1 text-xs"
                  >
                    Clear All
                  </button>
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {attributes.map(
                    (attribute) => (
                      <label
                        key={attribute.name}
                        className="flex cursor-pointer items-center gap-2 rounded-md border border-slate-200 p-3 hover:bg-slate-50"
                      >
                        <input
                          type="checkbox"
                          checked={selectedAttributes.includes(
                            attribute.name
                          )}
                          onChange={() =>
                            toggleAttribute(
                              attribute.name
                            )
                          }
                        />

                        <span className="text-sm text-slate-700">
                          {attribute.label}
                        </span>
                      </label>
                    )
                  )}
                </div>

                <p className="text-xs text-slate-500">
                  {selectedAttributes.length} of{" "}
                  {attributes.length} attributes
                  selected.
                </p>

              </div>
            )}

          <button
            className="btn-primary"
            onClick={
              handleStartProcessing
            }
            disabled={
              starting ||
              discovering ||
              (
                attributes.length > 0 &&
                selectedAttributes.length === 0
              )
            }
          >
            {starting
              ? "Starting Processing..."
              : `Process ${uploadedFiles.length} Files Together`}
          </button>

        </div>
      )}

    </div>
  );
}