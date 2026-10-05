import "./globals.css";

export const metadata = {
  title: "TalentEval — Technical Assessment Platform",
  description: "Voice-Based Technical Assessment Platform with LSA correctness and speech metrics evaluation",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="bg-decorations">
          <div className="bg-blob-1" />
          <div className="bg-blob-2" />
          <div className="bg-blob-3" />
        </div>
        <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
      </body>
    </html>
  );
}
