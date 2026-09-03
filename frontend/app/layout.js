import "./globals.css";

export const metadata = {
  title: "Voice Interview System",
  description: "Module 1 — scaffolding check",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
