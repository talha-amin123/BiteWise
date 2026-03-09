// BiteWise Content Script
// Extracts product info from Instacart product pages and checks for recalls

const API_URL = "http://127.0.0.1:5000/check";

function extractProductData() {
  const nameEl = document.querySelector("h1 span.e-1r7vnds");
  const productName = nameEl ? nameEl.textContent.trim() : null;

  const brandEl = document.querySelector("a.e-1451bcu span.e-10iahqc");
  const brand = brandEl ? brandEl.textContent.trim() : null;

  const sizeEl = document.querySelector("span.e-f17zur");
  const size = sizeEl ? sizeEl.textContent.trim() : null;

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
              ${recallInfo.recall_reason} • ${displayBrand} • ${formatDate(recallInfo.recall_date)}
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
              This specific product may not be affected • ${recallInfo.recall_reason} • ${formatDate(recallInfo.recall_date)}
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

function injectLoadingBanner() {
  const existing = document.getElementById("bitewise-banner");
  if (existing) existing.remove();

  const banner = document.createElement("div");
  banner.id = "bitewise-banner";
  banner.innerHTML = `
    <div style="
      background: #f8fafc;
      color: #475569;
      padding: 10px 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      border-bottom: 1px solid #e2e8f0;
      position: relative;
      z-index: 9999;
    ">
      <span style="font-size: 16px;">🔍</span>
      <span style="font-weight: 600;">BiteWise: Checking for recalls...</span>
    </div>
  `;

  const navbar = document.querySelector("header") || document.querySelector("[data-testid='header']");
  if (navbar && navbar.nextElementSibling) {
    navbar.parentNode.insertBefore(banner, navbar.nextElementSibling);
  } else {
    document.body.prepend(banner);
  }
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
    if (!response.ok) return null;
    return await response.json();
  } catch (err) {
    console.error("BiteWise: Could not reach API —", err.message);
    return null;
  }
}

async function run() {
  const data = extractProductData();
  console.log("🔍 BiteWise Extracted:", JSON.stringify(data, null, 2));

  if (!data.productName) {
    console.log("⚠️ BiteWise: Could not find product info on this page");
    return;
  }

  injectLoadingBanner();

  const result = await checkRecalls(data);

  if (!result) {
    const existing = document.getElementById("bitewise-banner");
    if (existing) existing.remove();
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
  const nameEl = document.querySelector("h1 span.e-1r7vnds");
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