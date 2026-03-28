// BiteWise Content Script
// Extracts product info from Instacart product pages and checks for recalls

const API_URL = "http://127.0.0.1:5000/check";

function textFromSelectors(selectors) {
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el && el.textContent && el.textContent.trim()) {
      return el.textContent.trim();
    }
  }
  return null;
}

function extractProductData() {
  const productName = textFromSelectors([
    "h1 span.e-1r7vnds",
    "h1",
    "[data-testid='product-details-product-name']",
    "[data-testid='item-details-name']",
  ]);

  const brand = textFromSelectors([
    "a.e-1451bcu span.e-10iahqc",
    "[data-testid='product-details-brand-name']",
    "[data-testid='item-details-brand']",
  ]);

  const size = textFromSelectors([
    "span.e-f17zur",
    "[data-testid='product-pack-size']",
    "[data-testid='item-details-size']",
  ]);

  return { productName, brand, size };
}

function formatDate(dateStr) {
  if (!dateStr) return "Unknown date";
  const clean = dateStr.split("T")[0];
  const parts = clean.split("-");
  if (parts.length !== 3) return dateStr;
  const d = new Date(parts[0], parts[1] - 1, parts[2]);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatRecallAge(ageDays) {
  if (ageDays === null || ageDays === undefined || Number.isNaN(Number(ageDays))) {
    return "Age unavailable";
  }

  const days = Number(ageDays);
  if (days === 0) return "Reported today";
  if (days === 1) return "1 day old";
  return `${days} days old`;
}

function injectBanner(level, recallInfo, instacartBrand) {
  const existing = document.getElementById("bitewise-banner");
  if (existing) existing.remove();

  const banner = document.createElement("div");
  banner.id = "bitewise-banner";

  const rawBrand = instacartBrand || (recallInfo ? recallInfo.recall_company_name : "");
  const displayBrand = rawBrand.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

  if (level === "high") {
    banner.innerHTML = `
      <div style="
        background: linear-gradient(135deg, #dc2626, #b91c1c);
        color: white;
        padding: 12px 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        position: relative;
        z-index: 9999;
      ">
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 20px;">⚠️</span>
          <div style="text-align: center;">
            <div style="font-weight: 700; font-size: 15px; margin-bottom: 2px;">
              RECALL ALERT — ${recallInfo.recall_source}
            </div>
            <div style="opacity: 0.95; font-size: 13px; font-weight: 600;">
              ${recallInfo.recall_reason} • ${displayBrand}
            </div>
            <div style="opacity: 0.92; font-size: 12px; font-weight: 700; margin-top: 4px;">
              Reported ${formatDate(recallInfo.recall_date)} • ${formatRecallAge(recallInfo.recall_age_days)}
            </div>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px; position: absolute; right: 24px;">
          <a href="${recallInfo.recall_url}" target="_blank" style="
            color: white;
            background: rgba(255,255,255,0.2);
            padding: 6px 14px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
          ">View Recall →</a>
          <button class="bitewise-close" style="
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 4px;
            opacity: 0.8;
          ">✕</button>
        </div>
      </div>
    `;
  } else if (level === "warning") {
    banner.innerHTML = `
      <div style="
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 12px 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        position: relative;
        z-index: 9999;
      ">
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 20px;">⚠️</span>
          <div style="text-align: center;">
            <div style="font-weight: 700; font-size: 15px; margin-bottom: 2px;">
              CAUTION — ${displayBrand} has active recalls
            </div>
            <div style="opacity: 0.95; font-size: 13px; font-weight: 600;">
              This specific product may not be affected • ${recallInfo.recall_reason}
            </div>
            <div style="opacity: 0.92; font-size: 12px; font-weight: 700; margin-top: 4px;">
              Reported ${formatDate(recallInfo.recall_date)} • ${formatRecallAge(recallInfo.recall_age_days)}
            </div>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px; position: absolute; right: 24px;">
          <a href="${recallInfo.recall_url}" target="_blank" style="
            color: white;
            background: rgba(255,255,255,0.2);
            padding: 6px 14px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
          ">View Recall →</a>
          <button class="bitewise-close" style="
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 4px;
            opacity: 0.8;
          ">✕</button>
        </div>
      </div>
    `;
  } else {
    banner.innerHTML = `
      <div style="
        background: #f0fdf4;
        color: #166534;
        padding: 10px 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        border-bottom: 1px solid #bbf7d0;
        position: relative;
        z-index: 9999;
      ">
        <span style="font-size: 16px;">✅</span>
        <span style="font-weight: 700;">BiteWise:</span>
        <span style="font-weight: 600;">No active recalls found for this product</span>
        <button class="bitewise-close" style="
          background: none;
          border: none;
          color: #166534;
          font-size: 16px;
          cursor: pointer;
          position: absolute;
          right: 24px;
          opacity: 0.6;
        ">✕</button>
      </div>
    `;
  }

  const navbar = document.querySelector("header") || document.querySelector("[data-testid='header']");
  if (navbar && navbar.nextElementSibling) {
    navbar.parentNode.insertBefore(banner, navbar.nextElementSibling);
  } else {
    document.body.prepend(banner);
  }

  banner.querySelector(".bitewise-close").addEventListener("click", () => banner.remove());
}

function injectStatusBanner(message, tone = "info") {
  const existing = document.getElementById("bitewise-banner");
  if (existing) existing.remove();

  const palette = {
    info: {
      background: "#f8fafc",
      color: "#475569",
      border: "#e2e8f0",
      icon: "🔍",
    },
    error: {
      background: "#fef2f2",
      color: "#991b1b",
      border: "#fecaca",
      icon: "⚠️",
    },
  };

  const style = palette[tone] || palette.info;
  const banner = document.createElement("div");
  banner.id = "bitewise-banner";
  banner.innerHTML = `
    <div style="
      background: ${style.background};
      color: ${style.color};
      padding: 10px 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      border-bottom: 1px solid ${style.border};
      position: relative;
      z-index: 9999;
    ">
      <span style="font-size: 16px;">${style.icon}</span>
      <span style="font-weight: 600;">${message}</span>
      <button class="bitewise-close" style="
        background: none;
        border: none;
        color: ${style.color};
        font-size: 16px;
        cursor: pointer;
        position: absolute;
        right: 24px;
        opacity: 0.6;
      ">✕</button>
    </div>
  `;

  const navbar = document.querySelector("header") || document.querySelector("[data-testid='header']");
  if (navbar && navbar.nextElementSibling) {
    navbar.parentNode.insertBefore(banner, navbar.nextElementSibling);
  } else {
    document.body.prepend(banner);
  }

  banner.querySelector(".bitewise-close").addEventListener("click", () => banner.remove());
}

function injectLoadingBanner() {
  injectStatusBanner("BiteWise: Checking for recalls...", "info");
}

async function checkRecalls(data) {
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        brand: data.brand,
        product_name: data.productName,
        size: data.size,
      }),
    });
    if (!response.ok) {
      return { error: `API request failed with status ${response.status}` };
    }
    return await response.json();
  } catch (err) {
    console.error("BiteWise: Could not reach API —", err.message);
    return { error: "Could not reach the local BiteWise API. Start api/app.py and refresh the page." };
  }
}

async function run() {
  const data = extractProductData();
  console.log("🔍 BiteWise Extracted:", JSON.stringify(data, null, 2));

  if (!data.productName) {
    console.log("⚠️ BiteWise: Could not find product info on this page");
    injectStatusBanner("BiteWise: Could not read this Instacart product page. The page structure may have changed.", "error");
    return;
  }

  injectLoadingBanner();

  const result = await checkRecalls(data);

  if (!result) {
    injectStatusBanner("BiteWise: No response received from the recall service.", "error");
    return;
  }

  if (result.error) {
    injectStatusBanner(`BiteWise: ${result.error}`, "error");
    return;
  }

  console.log(`🔍 BiteWise: ${result.match_count} match(es) found`);
  if (result.matches && result.matches.length > 0) {
    console.log("🔍 BiteWise Matches:", JSON.stringify(result.matches, null, 2));
  }

  if (result.matches && result.matches.length > 0) {
    const highMatch = result.matches.find(m => m.match_level === "high");
    const warningMatch = result.matches.find(m => m.match_level === "warning");

    if (highMatch) {
      injectBanner("high", highMatch, data.brand);
    } else if (warningMatch) {
      injectBanner("warning", warningMatch, data.brand);
    } else {
      injectBanner("safe", null, null);
    }
  } else {
    injectBanner("safe", null, null);
  }
}

// Retry logic and SPA navigation
let currentUrl = window.location.href;
let attempts = 0;
const maxAttempts = 5;

function tryExtract() {
  const nameEl = document.querySelector("h1 span.e-1r7vnds")
    || document.querySelector("h1")
    || document.querySelector("[data-testid='product-details-product-name']")
    || document.querySelector("[data-testid='item-details-name']");
  if (nameEl || attempts >= maxAttempts) {
    attempts = 0;
    run();
  } else {
    attempts++;
    setTimeout(tryExtract, 1000);
  }
}

// Only run on product pages
if (window.location.pathname.includes("/products/")) {
  tryExtract();
}

// Monitor for SPA navigation
const observer = new MutationObserver(() => {
  if (window.location.href !== currentUrl) {
    currentUrl = window.location.href;
    if (currentUrl.includes("/products/")) {
      attempts = 0;
      tryExtract();
    }
  }
});

observer.observe(document.body, { childList: true, subtree: true });
