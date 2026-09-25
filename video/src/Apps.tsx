import React from "react";
import { brand } from "./brand";

/** Premium UI recreations — recognizable, not screenshots of copyrighted products. */

const chrome = {
  font: brand.font,
  bar: "#1a1f2e",
  window: "#0d1220",
  border: "1px solid rgba(255,255,255,0.12)",
  muted: "rgba(255,255,255,0.45)",
  text: "#f4f6fb",
};

const WindowChrome: React.FC<{
  title: string;
  accent?: string;
  width: number;
  height: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ title, accent = brand.teal, width, height, children, style }) => (
  <div
    style={{
      width,
      height,
      borderRadius: 10,
      overflow: "hidden",
      background: chrome.window,
      border: chrome.border,
      boxShadow: "0 28px 70px rgba(0,0,0,0.55)",
      fontFamily: chrome.font,
      display: "flex",
      flexDirection: "column",
      ...style,
    }}
  >
    <div
      style={{
        height: 34,
        background: chrome.bar,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "0 12px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div style={{ display: "flex", gap: 5 }}>
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
          <div
            key={c}
            style={{ width: 9, height: 9, borderRadius: "50%", background: c, opacity: 0.85 }}
          />
        ))}
      </div>
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: 2,
          background: accent,
          marginLeft: 4,
        }}
      />
      <div style={{ color: chrome.muted, fontSize: 12, fontWeight: 500 }}>{title}</div>
    </div>
    <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>{children}</div>
  </div>
);

/** NetSuite-like: Finance / Period Close */
export const NetSuiteClose: React.FC<{ width?: number; height?: number; showCheck?: boolean }> = ({
  width = 520,
  height = 340,
  showCheck = true,
}) => (
  <WindowChrome title="NetSuite · Financial" accent="#1B4F72" width={width} height={height}>
    <div style={{ display: "flex", height: "100%" }}>
      <div
        style={{
          width: 120,
          background: "#0a1628",
          padding: 12,
          borderRight: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {["Home", "Financial", "Reports", "Setup"].map((item, i) => (
          <div
            key={item}
            style={{
              color: i === 1 ? chrome.text : chrome.muted,
              fontSize: 12,
              fontWeight: i === 1 ? 600 : 400,
              padding: "8px 6px",
              background: i === 1 ? "rgba(48,207,202,0.12)" : "transparent",
              borderRadius: 4,
              marginBottom: 2,
            }}
          >
            {item}
          </div>
        ))}
      </div>
      <div style={{ flex: 1, padding: 18 }}>
        <div style={{ color: chrome.muted, fontSize: 11, letterSpacing: "0.08em", marginBottom: 6 }}>
          ACCOUNTING PERIOD
        </div>
        <div style={{ color: chrome.text, fontSize: 22, fontWeight: 600, marginBottom: 16 }}>
          June 2026 · Close Period
        </div>
        {[
          ["Journal Entries", "Complete"],
          ["Revenue Recognition", "Complete"],
          ["Financial Statements", "Ready"],
        ].map(([label, status]) => (
          <div
            key={label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 0",
              borderBottom: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span style={{ color: chrome.text, fontSize: 14 }}>{label}</span>
            <span style={{ color: "#3DDC97", fontSize: 13, fontWeight: 600 }}>{status}</span>
          </div>
        ))}
        {showCheck && (
          <div
            style={{
              marginTop: 18,
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 14px",
              borderRadius: 8,
              background: "rgba(61,220,151,0.1)",
              border: "1px solid rgba(61,220,151,0.35)",
            }}
          >
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: "#3DDC97",
                color: "#04140c",
                fontWeight: 800,
                fontSize: 14,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              ✓
            </div>
            <div>
              <div style={{ color: chrome.text, fontSize: 14, fontWeight: 600 }}>
                Period Close Complete
              </div>
              <div style={{ color: chrome.muted, fontSize: 12 }}>Books locked · June 2026</div>
            </div>
          </div>
        )}
      </div>
    </div>
  </WindowChrome>
);

/** Excel-like forecast workbook */
export const ExcelForecast: React.FC<{ width?: number; height?: number }> = ({
  width = 540,
  height = 320,
}) => (
  <WindowChrome title="ARR Forecast_FINAL_v9.xlsx" accent="#217346" width={width} height={height}>
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div
        style={{
          display: "flex",
          gap: 0,
          background: "#141a28",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          paddingLeft: 36,
        }}
      >
        {["Revenue Forecast", "Bookings", "Headcount", "Cash Flow"].map((tab, i) => (
          <div
            key={tab}
            style={{
              padding: "8px 14px",
              fontSize: 11,
              color: i === 0 ? chrome.text : chrome.muted,
              background: i === 0 ? chrome.window : "transparent",
              borderTop: i === 0 ? `2px solid #217346` : "2px solid transparent",
            }}
          >
            {tab}
          </div>
        ))}
      </div>
      <div style={{ display: "flex", flex: 1 }}>
        <div style={{ width: 28, background: "#121722", borderRight: "1px solid rgba(255,255,255,0.05)" }} />
        <div style={{ flex: 1, padding: 8 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1.4fr repeat(4, 1fr)", gap: 2 }}>
            {["", "Q1", "Q2", "Q3", "Q4"].map((h) => (
              <div
                key={h || "blank"}
                style={{
                  background: "#1a2336",
                  color: chrome.muted,
                  fontSize: 11,
                  padding: "6px 8px",
                  fontWeight: 600,
                }}
              >
                {h}
              </div>
            ))}
            {[
              ["New ARR", "2.1", "2.4", "2.8", "3.1"],
              ["Expansion", "0.8", "1.1", "0.9", "1.4"],
              ["Churn", "(0.3)", "(0.4)", "(0.3)", "(0.5)"],
              ["Ending ARR", "18.1", "18.7", "19.4", "20.2"],
            ].map((row) =>
              row.map((cell, j) => (
                <div
                  key={`${row[0]}-${j}`}
                  style={{
                    background: j === 0 ? "#151b2a" : row[0] === "Ending ARR" ? "rgba(48,207,202,0.12)" : "#0f1522",
                    color: j === 0 ? chrome.muted : chrome.text,
                    fontSize: 12,
                    padding: "7px 8px",
                    fontWeight: row[0] === "Ending ARR" ? 700 : 400,
                    borderBottom: "1px solid rgba(255,255,255,0.03)",
                  }}
                >
                  {cell}
                  {j > 0 && row[0] !== "Churn" ? "M" : j > 0 && row[0] === "Churn" ? "M" : ""}
                </div>
              )),
            )}
          </div>
        </div>
      </div>
    </div>
  </WindowChrome>
);

/** PowerPoint-like board deck */
export const PowerPointDeck: React.FC<{ width?: number; height?: number }> = ({
  width = 480,
  height = 300,
}) => (
  <WindowChrome title="Board Meeting — July Executive Review.pptx" accent="#C43E1C" width={width} height={height}>
    <div style={{ padding: 20, height: "100%", background: "linear-gradient(160deg, #10182a, #0a0f1c)" }}>
      <div style={{ color: brand.teal, fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", marginBottom: 8 }}>
        Q3 FORECAST
      </div>
      <div style={{ color: chrome.text, fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em", marginBottom: 6 }}>
        July Executive Review
      </div>
      <div style={{ color: chrome.muted, fontSize: 13, marginBottom: 20 }}>Board Meeting · Draft</div>
      <div style={{ display: "flex", gap: 12 }}>
        {[
          { label: "ARR", val: "$18.7M" },
          { label: "NRR", val: "118%" },
          { label: "Cash", val: "$42M" },
        ].map((kpi) => (
          <div
            key={kpi.label}
            style={{
              flex: 1,
              padding: "12px 10px",
              borderRadius: 8,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div style={{ color: chrome.muted, fontSize: 11 }}>{kpi.label}</div>
            <div style={{ color: chrome.text, fontSize: 18, fontWeight: 700 }}>{kpi.val}</div>
          </div>
        ))}
      </div>
    </div>
  </WindowChrome>
);

/** Salesforce-like pipeline */
export const SalesforcePipeline: React.FC<{ width?: number; height?: number }> = ({
  width = 500,
  height = 300,
}) => (
  <WindowChrome title="Sales · Pipeline Dashboard" accent="#00A1E0" width={width} height={height}>
    <div style={{ display: "flex", height: "100%" }}>
      <div style={{ width: 48, background: "#032d60", paddingTop: 12 }}>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              width: 22,
              height: 22,
              margin: "10px auto",
              borderRadius: 4,
              background: i === 1 ? "#00A1E0" : "rgba(255,255,255,0.15)",
            }}
          />
        ))}
      </div>
      <div style={{ flex: 1, padding: 14 }}>
        <div style={{ color: chrome.text, fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
          Pipeline Dashboard
        </div>
        <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
          {[
            { l: "Bookings", v: "$4.2M" },
            { l: "Closed Won", v: "23" },
            { l: "Forecast", v: "$6.1M" },
          ].map((c) => (
            <div
              key={c.l}
              style={{
                flex: 1,
                background: "#132038",
                borderRadius: 6,
                padding: "10px 8px",
                border: "1px solid rgba(0,161,224,0.25)",
              }}
            >
              <div style={{ color: chrome.muted, fontSize: 10 }}>{c.l}</div>
              <div style={{ color: chrome.text, fontSize: 16, fontWeight: 700 }}>{c.v}</div>
            </div>
          ))}
        </div>
        {["Discovery", "Proposal", "Negotiation", "Closed Won"].map((stage, i) => (
          <div key={stage} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <div style={{ width: 70, color: chrome.muted, fontSize: 11 }}>{stage}</div>
            <div
              style={{
                flex: 1,
                height: 14,
                borderRadius: 3,
                background: "rgba(255,255,255,0.06)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${35 + i * 15}%`,
                  height: "100%",
                  background: i === 3 ? "#3DDC97" : "#00A1E0",
                  opacity: 0.85,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  </WindowChrome>
);

export const SlackToast: React.FC<{ from: string; message: string }> = ({ from, message }) => (
  <div
    style={{
      width: 340,
      background: "#1a1d21",
      borderRadius: 12,
      border: "1px solid rgba(255,255,255,0.1)",
      padding: "12px 14px",
      boxShadow: "0 16px 40px rgba(0,0,0,0.45)",
      fontFamily: chrome.font,
    }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
      <div
        style={{
          width: 22,
          height: 22,
          borderRadius: 6,
          background: "#4A154B",
          color: "#fff",
          fontSize: 11,
          fontWeight: 800,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        S
      </div>
      <div style={{ color: chrome.muted, fontSize: 12, fontWeight: 600 }}>Slack · #fpna</div>
    </div>
    <div style={{ color: chrome.text, fontSize: 13 }}>
      <strong style={{ fontWeight: 700 }}>{from}</strong>
      <span style={{ color: chrome.muted }}>  ·  just now</span>
    </div>
    <div style={{ color: chrome.text, fontSize: 14, marginTop: 4 }}>{message}</div>
  </div>
);

export const OutlookToast: React.FC<{ subject: string; preview: string }> = ({
  subject,
  preview,
}) => (
  <div
    style={{
      width: 340,
      background: "#1b222d",
      borderRadius: 12,
      border: "1px solid rgba(255,255,255,0.1)",
      padding: "12px 14px",
      boxShadow: "0 16px 40px rgba(0,0,0,0.45)",
      fontFamily: chrome.font,
    }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
      <div
        style={{
          width: 22,
          height: 22,
          borderRadius: 5,
          background: "#0078D4",
          color: "#fff",
          fontSize: 11,
          fontWeight: 800,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        O
      </div>
      <div style={{ color: chrome.muted, fontSize: 12, fontWeight: 600 }}>Outlook</div>
    </div>
    <div style={{ color: chrome.text, fontSize: 14, fontWeight: 600 }}>{subject}</div>
    <div style={{ color: chrome.muted, fontSize: 13, marginTop: 3 }}>{preview}</div>
  </div>
);

export const CalendarToast: React.FC<{ title: string; when: string }> = ({ title, when }) => (
  <div
    style={{
      width: 340,
      background: "#1c2430",
      borderRadius: 12,
      border: "1px solid rgba(255,255,255,0.1)",
      padding: "12px 14px",
      boxShadow: "0 16px 40px rgba(0,0,0,0.45)",
      fontFamily: chrome.font,
    }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
      <div
        style={{
          width: 22,
          height: 22,
          borderRadius: 5,
          background: "#039BE5",
          color: "#fff",
          fontSize: 10,
          fontWeight: 800,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        31
      </div>
      <div style={{ color: chrome.muted, fontSize: 12, fontWeight: 600 }}>Calendar</div>
    </div>
    <div style={{ color: chrome.text, fontSize: 14, fontWeight: 600 }}>{title}</div>
    <div style={{ color: chrome.muted, fontSize: 13, marginTop: 3 }}>{when}</div>
  </div>
);

export const BrowserTabs: React.FC<{ count?: number }> = ({ count = 8 }) => (
  <div
    style={{
      display: "flex",
      gap: 2,
      background: "#121722",
      borderRadius: "10px 10px 0 0",
      padding: "6px 8px 0",
      border: chrome.border,
      borderBottom: "none",
      width: 560,
      fontFamily: chrome.font,
    }}
  >
    {Array.from({ length: Math.min(count, 10) }).map((_, i) => (
      <div
        key={i}
        style={{
          flex: i === 0 ? 1.3 : 1,
          height: 28,
          borderRadius: "6px 6px 0 0",
          background: i === 0 ? chrome.window : "#1a2030",
          color: chrome.muted,
          fontSize: 10,
          display: "flex",
          alignItems: "center",
          padding: "0 8px",
          overflow: "hidden",
          whiteSpace: "nowrap",
        }}
      >
        {i === 0
          ? "ARR waterfall — sheet"
          : i === 1
            ? "Board comments"
            : i === 2
              ? "Pipeline export"
              : `Report ${i}`}
      </div>
    ))}
  </div>
);
