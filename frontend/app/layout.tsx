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
      <body>{children}</body>
    </html>
  );
}
