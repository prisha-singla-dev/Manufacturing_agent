import "./globals.css";

export const metadata = {
  title: "Manufacturing Agent",
  description: "Inventory & procurement chat agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
