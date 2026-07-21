"use client"

import { createContext, useContext } from "react"

type ShellChrome = {
  sidebarOpen: boolean
  toggleSidebar: () => void
}

const ShellChromeContext = createContext<ShellChrome>({
  sidebarOpen: true,
  toggleSidebar: () => undefined,
})

export function ShellChromeProvider({
  value,
  children,
}: {
  value: ShellChrome
  children: React.ReactNode
}) {
  return (
    <ShellChromeContext.Provider value={value}>{children}</ShellChromeContext.Provider>
  )
}

export function useShellChrome() {
  return useContext(ShellChromeContext)
}
