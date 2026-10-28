import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"

// Follow the OS light/dark setting (shadcn themes key off the .dark class).
const mq = matchMedia("(prefers-color-scheme: dark)")
const applyTheme = () => document.documentElement.classList.toggle("dark", mq.matches)
applyTheme(); mq.addEventListener("change", applyTheme)

// App imports the dataset with top-level await, so load it after the theme is set.
const { default: App } = await import("./App.tsx")
createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>)
