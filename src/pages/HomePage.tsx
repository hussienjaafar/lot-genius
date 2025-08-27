import React from "react";

const HomePage: React.FC = () => {
  return (
    <div className="home-page">
      <div className="hero-section">
        <h1>Welcome to Lot Genius</h1>
        <p className="hero-subtitle">
          Smart lot management and ROI optimization for resellers
        </p>

        <div className="features-grid">
          <div className="feature-card">
            <h3>📊 Pipeline Processing</h3>
            <p>
              Upload CSV files and process them through our intelligent pricing
              pipeline
            </p>
          </div>

          <div className="feature-card">
            <h3>🎯 ROI Optimization</h3>
            <p>Get optimal bid recommendations based on Monte Carlo analysis</p>
          </div>

          <div className="feature-card">
            <h3>📈 Reports Dashboard</h3>
            <p>
              View detailed reports with executive summaries and investment
              decisions
            </p>
          </div>
        </div>

        <div className="quick-actions">
          <a href="/pipeline" className="btn btn-primary">
            Start Processing
          </a>
          <a href="/reports" className="btn btn-secondary">
            View Reports
          </a>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
