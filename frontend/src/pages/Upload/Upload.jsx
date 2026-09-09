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


  const handleUpload = async (files) => {
    if (uploading) {
      return;
    }

    setError(null);
    setUploading(true);
    setProgress(0);

    try {
      const result =
        await fileService.uploadBatch(
          files,
          setProgress
        );

      setUploadedFiles(
        result.files || []
      );

    } catch (err) {
      setError(err);

    } finally {
      setUploading(false);
    }
  };


  const handleStartProcessing =
    async () => {

      if (
        starting ||
        uploadedFiles.length === 0
      ) {
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
            fileIds
          );

        const jobIds =
          result.jobs.map(
            (job) => job.id
          );

        /*
         * Pass the job IDs through the URL.
         * Processing page will poll the whole batch.
         */
        navigate(
          `/processing/batch?job_ids=${jobIds.join(
            ","
          )}`
        );

      } catch (err) {
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
        <div className="card space-y-4">

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

          <button
            className="btn-primary"
            onClick={
              handleStartProcessing
            }
            disabled={starting}
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