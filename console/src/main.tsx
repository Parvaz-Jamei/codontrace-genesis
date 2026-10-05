import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BenchApp } from "./components/bench/bench-app";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("root missing");

createRoot(root).render(
  <StrictMode>
    <BenchApp />
  </StrictMode>,
);
