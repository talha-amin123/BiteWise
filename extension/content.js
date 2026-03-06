// BiteWise Content Script
// Product page: extracts info and shows recall banner
// Cart page: scans cart items and shows summary card

const API_URL = "http://127.0.0.1:5000/check";

// ========== SHARED UTILITIES ==========

function formatDate(dateStr) {
  if (!dateStr) return "Unknown date";
  const clean = dateStr.split("T")[0];
  const parts = clean.split("-");
  if (parts.length !== 3) return dateStr;
  const d = new Date(parts[0], parts[1] - 1, parts[2]);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

async function checkRecalls(brand, productName, size) {
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        brand: brand || "",
        product_name: productName || "",
        size: size || "",
      }),
    });
    if (!response.ok) return null;
    return await response.json();
  } catch (err) {
    console.error("BiteWise: Could not reach API —", err.message);
    return null;
  }
}

// ========== PRODUCT PAGE ==========

function extractProductData() {
  const nameEl = document.querySelector("h1 span.e-1r7vnds");
  const productName = nameEl ? nameEl.textContent.trim() : null;

  const brandEl = document.querySelector("a.e-1451bcu span.e-10iahqc");
  const brand = brandEl ? brandEl.textContent.trim() : null;

  const sizeEl = document.querySelector("span.e-f17zur");
  const size = sizeEl ? sizeEl.textContent.trim() : null;

  return { productName, brand, size };
}

function injectProductBanner(level, recallInfo, instacartBrand) {
  const existing = document.getElementById("bitewise-banner");
  if (existing) existing.remove();

  const banner = document.createElement("div");
  banner.id = "bitewise-banner";

  // Use the brand name from Instacart page, not from API
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

async function runProductPage() {
  const data = extractProductData();
  console.log("🔍 BiteWise Extracted:", JSON.stringify(data, null, 2));

  if (!data.productName) {
    console.log("⚠️ BiteWise: Could not find product info on this page");
    return;
  }

  injectLoadingBanner();

  const result = await checkRecalls(data.brand, data.productName, data.size);

  if (!result) {
    const existing = document.getElementById("bitewise-banner");
    if (existing) existing.remove();
    return;
  }

  console.log(`🔍 BiteWise: ${result.match_count} match(es) found`);

  if (result.matches && result.matches.length > 0) {
    const highMatch = result.matches.find(m => m.match_level === "high");
    const warningMatch = result.matches.find(m => m.match_level === "warning");

    if (highMatch) {
      injectProductBanner("high", highMatch, data.brand);
    } else if (warningMatch) {
      injectProductBanner("warning", warningMatch, data.brand);
    } else {
      injectProductBanner("safe", null, null);
    }
  } else {
    injectProductBanner("safe", null, null);
  }
}

// ========== CART PAGE ==========

function extractCartItems() {
  const items = [];
  const cartGroups = document.querySelectorAll('div[role="group"].e-b311fy');

  cartGroups.forEach(group => {
    const nameEl = group.querySelector("h3.e-z2c0se");
    if (nameEl) {
      const fullName = nameEl.textContent.trim();
      // Remove trailing size info in parentheses like "(1.15 oz)" or "(each)"
      const cleanName = fullName.replace(/\s*\([^)]*\)\s*$/, "").trim();
      items.push({ fullName: cleanName });
    }
  });

  return items;
}

function buildCartCard(results, totalItems) {
  const recalled = results.filter(r => r.level === "high");
  const caution = results.filter(r => r.level === "warning");
  const safeCount = totalItems - recalled.length - caution.length;
  const flaggedCount = recalled.length + caution.length;

  let itemsHtml = "";

  // Recalled items
  if (recalled.length > 0) {
    itemsHtml += `<div style="font-weight: 700; font-size: 13px; color: #dc2626; margin-bottom: 8px;">RECALLED (${recalled.length})</div>`;
    recalled.forEach(item => {
      itemsHtml += `
        <div style="
          background: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 8px;
          padding: 10px 12px;
          margin-bottom: 8px;
        ">
          <div style="display: flex; align-items: start; gap: 8px;">
            <span style="font-size: 14px; margin-top: 1px;">🔴</span>
            <div style="flex: 1;">
              <div style="font-weight: 600; font-size: 13px; color: #1f2937; margin-bottom: 2px;">
                ${item.name}
              </div>
              <div style="font-size: 12px; color: #6b7280;">
                ${item.match.recall_reason}
              </div>
              <a href="${item.match.recall_url}" target="_blank" style="
                font-size: 12px;
                color: #dc2626;
                text-decoration: none;
                font-weight: 600;
              ">View Recall →</a>
            </div>
          </div>
        </div>
      `;
    });
  }

  // Caution items
  if (caution.length > 0) {
    itemsHtml += `<div style="font-weight: 700; font-size: 13px; color: #d97706; margin-bottom: 8px; ${recalled.length > 0 ? 'margin-top: 12px;' : ''}">CAUTION (${caution.length})</div>`;
    caution.forEach(item => {
      itemsHtml += `
        <div style="
          background: #fffbeb;
          border: 1px solid #fde68a;
          border-radius: 8px;
          padding: 10px 12px;
          margin-bottom: 8px;
        ">
          <div style="display: flex; align-items: start; gap: 8px;">
            <span style="font-size: 14px; margin-top: 1px;">🟡</span>
            <div style="flex: 1;">
              <div style="font-weight: 600; font-size: 13px; color: #1f2937; margin-bottom: 2px;">
                ${item.name}
              </div>
              <div style="font-size: 12px; color: #6b7280;">
                Brand has active recalls • ${item.match.recall_reason}
              </div>
              <a href="${item.match.recall_url}" target="_blank" style="
                font-size: 12px;
                color: #d97706;
                text-decoration: none;
                font-weight: 600;
              ">View Recall →</a>
            </div>
          </div>
        </div>
      `;
    });
  }

  // Safe items
  if (safeCount > 0) {
    itemsHtml += `
      <div style="
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
        ${flaggedCount > 0 ? 'margin-top: 8px;' : ''}
        font-size: 13px;
        color: #166534;
      ">
        <span>✅</span>
        <span style="font-weight: 600;">${safeCount} other item${safeCount > 1 ? 's' : ''} — no recalls</span>
      </div>
    `;
  }

  // Header color based on severity
  let headerBg, headerColor;
  if (recalled.length > 0) {
    headerBg = "#dc2626";
    headerColor = "white";
  } else if (caution.length > 0) {
    headerBg = "#f59e0b";
    headerColor = "white";
  } else {
    headerBg = "#16a34a";
    headerColor = "white";
  }

  return `
    <div style="
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.1);
      overflow: hidden;
      margin: 16px;
      max-width: 360px;
    ">
      <div style="
        background: ${headerBg};
        color: ${headerColor};
        padding: 12px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      ">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">${recalled.length > 0 ? '⚠️' : caution.length > 0 ? '⚠️' : '✅'}</span>
          <span style="font-weight: 700; font-size: 14px;">BiteWise Cart Check</span>
        </div>
        <div style="
          background: rgba(255,255,255,0.25);
          padding: 2px 10px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 700;
        ">${flaggedCount}/${totalItems}</div>
      </div>
      <div style="padding: 14px 16px; max-height: 400px; overflow-y: auto;">
        ${itemsHtml}
      </div>
    </div>
  `;
}

function injectCartCard(html) {
  const existing = document.getElementById("bitewise-cart-card");
  if (existing) existing.remove();

  const container = document.createElement("div");
  container.id = "bitewise-cart-card";
  container.style.cssText = "position: fixed; bottom: 20px; left: 20px; z-index: 99999;";
  container.innerHTML = html;

  document.body.appendChild(container);
}

function injectCartLoading() {
  const existing = document.getElementById("bitewise-cart-card");
  if (existing) existing.remove();

  const container = document.createElement("div");
  container.id = "bitewise-cart-card";
  container.style.cssText = "position: fixed; bottom: 20px; left: 20px; z-index: 99999;";
  container.innerHTML = `
    <div style="
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.1);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 10px;
      max-width: 360px;
      margin: 16px;
    ">
      <span style="font-size: 18px;">🔍</span>
      <span style="font-weight: 600; font-size: 14px; color: #475569;">BiteWise: Scanning cart items...</span>
    </div>
  `;

  document.body.appendChild(container);
}

async function runCartPage() {
  const items = extractCartItems();
  console.log(`🛒 BiteWise: Found ${items.length} items in cart`);

  if (items.length === 0) {
    console.log("⚠️ BiteWise: No cart items found");
    return;
  }

  injectCartLoading();

  const results = [];

  for (const item of items) {
    console.log(`  → Checking: ${item.fullName}`);
    const result = await checkRecalls("", item.fullName, "");

    if (result && result.matches && result.matches.length > 0) {
      const highMatch = result.matches.find(m => m.match_level === "high");
      const warningMatch = result.matches.find(m => m.match_level === "warning");

      if (highMatch) {
        results.push({ name: item.fullName, level: "high", match: highMatch });
      } else if (warningMatch) {
        results.push({ name: item.fullName, level: "warning", match: warningMatch });
      }
    }
  }

  console.log(`🛒 BiteWise: ${results.length} flagged out of ${items.length} items`);

  const cardHtml = buildCartCard(results, items.length);
  injectCartCard(cardHtml);
}

// ========== PAGE DETECTION & ROUTING ==========

function isProductPage() {
  return window.location.pathname.includes("/products/");
}

function isCartPage() {
  return window.location.href.includes("cart_id=") || window.location.pathname.includes("/storefront");
}

function route() {
  // Clean up previous UI
  const banner = document.getElementById("bitewise-banner");
  if (banner) banner.remove();
  const card = document.getElementById("bitewise-cart-card");
  if (card) card.remove();

  if (isProductPage()) {
    console.log("🔍 BiteWise: Product page detected");
    tryExtractProduct();
  } else if (isCartPage()) {
    console.log("🛒 BiteWise: Cart page detected");
    tryExtractCart();
  }
}

// Retry logic for product pages (SPA — DOM may not be ready)
let productAttempts = 0;
const maxAttempts = 5;

function tryExtractProduct() {
  const nameEl = document.querySelector("h1 span.e-1r7vnds");
  if (nameEl || productAttempts >= maxAttempts) {
    productAttempts = 0;
    runProductPage();
  } else {
    productAttempts++;
    setTimeout(tryExtractProduct, 1000);
  }
}

// Retry logic for cart pages
let cartAttempts = 0;

function tryExtractCart() {
  const cartItems = document.querySelectorAll('div[role="group"].e-b311fy');
  if (cartItems.length > 0 || cartAttempts >= maxAttempts) {
    cartAttempts = 0;
    runCartPage();
  } else {
    cartAttempts++;
    setTimeout(tryExtractCart, 1000);
  }
}

// Initial run
route();

// Monitor for SPA navigation
let currentUrl = window.location.href;

const observer = new MutationObserver(() => {
  if (window.location.href !== currentUrl) {
    currentUrl = window.location.href;
    route();
  }
});

observer.observe(document.body, { childList: true, subtree: true });