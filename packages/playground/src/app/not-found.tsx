"use client";

export const dynamic = "force-dynamic";

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: "60vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "sans-serif",
        color: "#002855",
      }}
    >
      <h1 style={{ fontSize: "3rem", fontWeight: "bold", margin: 0 }}>404</h1>
      <p style={{ marginTop: "0.5rem", opacity: 0.6 }}>Page not found.</p>
      <a
        href="/"
        style={{
          marginTop: "1.5rem",
          padding: "0.5rem 1.5rem",
          background: "#002855",
          color: "white",
          borderRadius: "0.5rem",
          textDecoration: "none",
          fontSize: "0.875rem",
        }}
      >
        Return Home
      </a>
    </div>
  );
}
