// src/pages/ProcessingHistory/ProcessingHistory.jsx

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { processingService } from "../../services/processingService";

function ProcessingHistory() {
  const navigate = useNavigate();

  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      setLoading(true);
      setError("");

      const data = await processingService.history();

      setBatches(data.results ?? data);
    } catch (err) {
      console.error(err);
      setError(
        "Unable to load processing history."
      );
    } finally {
      setLoading(false);
    }
  }

  function openBatch(batchId) {
    navigate(`/data?batch_id=${batchId}`);
  }

  function openChatbot(batchId) {
    navigate(`/chatbot?batch_id=${batchId}`);
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          Processing History
        </h1>

        <button
          onClick={() => navigate("/upload")}
          className="rounded bg-blue-600 px-4 py-2 text-white"
        >
          New Processing
        </button>
      </div>

      {loading && (
        <div className="mt-6 rounded border p-6">
          Loading processing history...
        </div>
      )}

      {error && (
        <div className="mt-4 rounded border border-red-300 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      {!loading &&
        !error &&
        batches.length === 0 && (
          <div className="mt-6 rounded border p-6">
            No processing history available.
          </div>
        )}

      {!loading &&
        batches.length > 0 && (
          <div className="mt-6 space-y-4">
            {batches.map((batch) => (
              <div
                key={batch.id}
                className="rounded-lg border bg-white p-5 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold">
                      {batch.name ||
                        `Processing Batch ${batch.id}`}
                    </h2>

                    <p className="mt-1 text-sm text-gray-600">
                      Batch ID: {batch.id}
                    </p>

                    <p className="text-sm text-gray-600">
                      Files: {batch.file_count ?? 0}
                    </p>

                    <p className="text-sm text-gray-600">
                      Jobs: {batch.job_count ?? 0}
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="rounded-full bg-gray-100 px-3 py-1 text-sm">
                      {batch.status}
                    </span>

                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() =>
                          openBatch(batch.id)
                        }
                        className="rounded bg-blue-600 px-4 py-2 text-white"
                      >
                        View Data
                      </button>

                      <button
                        onClick={() =>
                          openChatbot(batch.id)
                        }
                        className="rounded bg-purple-600 px-4 py-2 text-white"
                      >
                        Chatbot
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
    </div>
  );
}

export default ProcessingHistory;