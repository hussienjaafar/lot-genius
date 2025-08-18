import React from "react";

const HomePage: React.FC = () => {
  return (
    <div className="home-page">
      <header className="header">
        <h1>Welcome to Lot Genius</h1>
        <p>Smart lot management made simple</p>
      </header>
      <main className="main-content">
        <section className="hero-section">
          <h2>Manage Your Lots Efficiently</h2>
          <p>
            Track, organize, and optimize your lot operations with our
            intelligent platform.
          </p>
          <button className="cta-button">Get Started</button>
        </section>
      </main>
    </div>
  );
};

export default HomePage;
