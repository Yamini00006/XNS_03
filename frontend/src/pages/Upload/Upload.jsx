// src/pages/Upload/Upload.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import FileUpload from "../../components/FileUpload/FileUpload";
import ErrorMessage from "../../components/ErrorMessage/ErrorMessage";
import { fileService } from "../../services/fileService";
import { processingService } from "../../services/processingService";
import { formatBytes } from "../../utils/formatters";

export default function Upload() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);

  const handleUpload = async (file) => {
    if (uploading) return; // prevent duplicate submissions
    setError(null);
    setUploading(true);
    setProgress(0);
    try {
      const result = await fileService.upload(file, setProgress);
      setUploadedFile(result);
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  };

  const handleStartProcessing = async () => {
    if (starting || !uploadedFile) return;
    setStarting(true);
    setError(null);
    try {
      const job = await processingService.start(uploadedFile.id);
      navigate(`/processing/${job.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-lg font-semibold text-slate-800">Upload a File</h1>

      <FileUpload onUpload={handleUpload} uploading={uploading} progress={progress} />

      {error && <ErrorMessage error={error} />}

      {uploadedFile && (
        <div className="card space-y-3">
          <p className="text-sm text-green-700">Upload successful.</p>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-slate-500">File</dt>
            <dd>{uploadedFile.original_name}</dd>
            <dt className="text-slate-500">Format</dt>
            <dd className="uppercase">{uploadedFile.file_format}</dd>
            <dt className="text-slate-500">Size</dt>
            <dd>{formatBytes(uploadedFile.file_size_bytes)}</dd>
          </dl>
          <button className="btn-primary" onClick={handleStartProcessing} disabled={starting}>
            {starting ? "Starting..." : "Start Processing"}
          </button>
        </div>
      )}
    </div>
  );
}
