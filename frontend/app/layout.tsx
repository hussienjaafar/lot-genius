import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lot Genius",
  description: "B-Stock analysis and optimization",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="bg-white border-b border-gray-200">
          <div className="mx-auto max-w-6xl px-6">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-8">
                <div className="text-xl font-bold text-gray-900">
                  Lot Genius
                </div>
                <div className="flex space-x-6">
                  <a
                    href="/"
                    className="text-gray-700 hover:text-blue-600 font-medium transition-colors"
                  >
                    Home
                  </a>
                  <a
                    href="/calibration"
                    className="text-gray-700 hover:text-blue-600 font-medium transition-colors"
                  >
                    Calibration
                  </a>
                </div>
              </div>
            </div>
          </div>
        </nav>
        <div className="min-h-screen bg-gray-50">{children}</div>
      </body>
    </html>
  );
}
