import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import HomePage from "@pages/HomePage";
import OptimizePage from "@pages/OptimizePage";
import PipelinePage from "@pages/PipelinePage";
import ReportsPage from "@pages/ReportsPage";
import "./styles/App.css";

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">
            <Link to="/">Lot Genius</Link>
          </div>
          <ul className="nav-links">
            <li>
              <Link to="/">Home</Link>
            </li>
            <li>
              <Link to="/optimize">Optimize</Link>
            </li>
            <li>
              <Link to="/pipeline">Pipeline</Link>
            </li>
            <li>
              <Link to="/reports">Reports</Link>
            </li>
          </ul>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/optimize" element={<OptimizePage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
