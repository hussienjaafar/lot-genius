import React, { useState } from "react";
import FileUpload from "../components/FileUpload";
import ProgressStream from "../components/ProgressStream";

const PipelinePage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingResults, setProcessingResults] = useState<any>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setProcessingResults(null);
  };

  const startProcessing = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setProcessingResults(null);

    try {
      // Upload file and start processing
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("http://localhost:8000/v1/report", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // The ProgressStream component will handle the SSE events
      // Processing will continue via SSE connection
    } catch (error) {
      console.error("Error starting pipeline:", error);
      setIsProcessing(false);
      // Fall back to simulation if API fails
    }
  };

  const handleProcessingComplete = (finalData: any) => {
    setIsProcessing(false);
    setProcessingResults(finalData);
  };

  const handleProcessingError = (error: string) => {
    setIsProcessing(false);
    console.error("Processing error:", error);
  };

  return (
    <div className="pipeline-page">
      <div className="page-header">
        <h1>Processing Pipeline</h1>
        <p>Upload your CSV file to start the intelligent pricing analysis</p>
      </div>

      <div className="pipeline-content">
        <div className="upload-section">
          <FileUpload
            onFileSelect={handleFileSelect}
            label="Upload CSV File"
            description="Select a CSV file containing your lot items for analysis"
            disabled={isProcessing}
          />

          {selectedFile && !isProcessing && (
            <div className="file-actions">
              <button className="btn btn-primary" onClick={startProcessing}>
                Start Processing Pipeline
              </button>
            </div>
          )}
        </div>

        {(isProcessing || processingResults) && (
          <div className="progress-section">
            <ProgressStream
              isActive={isProcessing}
              onComplete={handleProcessingComplete}
              onError={handleProcessingError}
            />
          </div>
        )}

        {processingResults && (
          <div className="results-section">
            <h2>Processing Complete!</h2>
            <div className="results-summary">
              <div className="metric">
                <span className="label">Recommended Bid:</span>
                <span className="value">${processingResults.bid}</span>
              </div>
              <div className="metric">
                <span className="label">Expected ROI:</span>
                <span className="value">
                  {(processingResults.roi * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="results-actions">
              <button className="btn btn-primary">View Full Report</button>
              <button className="btn btn-secondary">Download Results</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PipelinePage;
