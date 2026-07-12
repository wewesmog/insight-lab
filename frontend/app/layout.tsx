import type { Metadata } from "next"

import "./globals.css"

export const metadata: Metadata = {
  title: "Insight Lab",
  description: "Beyond positive/negative — verbatim insights powered by LangGraph",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
