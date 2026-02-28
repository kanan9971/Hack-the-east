const rawApiBase = import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8001";

export const API_BASE = rawApiBase.replace(/\/+$/, "");
