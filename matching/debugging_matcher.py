# import sqlite3
# import sys
# from rapidfuzz import fuzz

# DB_PATH = "data/bitewise.db"


# def normalize(text):
#     if not text:
#         return ""
#     return " ".join(text.lower().split())


# def debug_match(brand, product_name):
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row

#     brand_norm = normalize(brand)
#     product_norm = normalize(product_name)

#     # Search for recalls where brand/company/announcement contains the brand
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT
#             r.recall_id,
#             r.recall_source,
#             r.recall_announcement_title,
#             r.recall_reason,
#             r.recall_brand_name,
#             r.recall_company_name,
#             r.recall_announcement_text,
#             p.product_id,
#             p.product_description,
#             p.raw_detail
#         FROM recalls r
#         JOIN products p ON r.recall_id = p.recall_id
#         WHERE
#             LOWER(r.recall_brand_name) LIKE "hormel foods corporation"
#             OR LOWER(r.recall_company_name) LIKE "hormel foods corporation"
#     """)

#     rows = cursor.fetchall()
#     conn.close()

#     if not rows:
#         print(f"\n❌ No records found containing '{brand}' in brand, company, or announcement text")
#         return

#     print(f"\n{'='*80}")
#     print(f"DEBUG: brand='{brand}' | product='{product_name}'")
#     print(f"Normalized: brand='{brand_norm}' | product='{product_norm}'")
#     print(f"Found {len(rows)} product rows matching '{brand}' in DB")
#     print(f"{'='*80}")

#     for row in rows:
#         print(f"\n{'─'*80}")
#         print(f"Recall #{row['recall_id']} | Product #{row['product_id']} | {row['recall_source']}")
#         print(f"Title: {(row['recall_announcement_title'] or '')[:100]}")
#         print(f"DB Brand: {row['recall_brand_name']}")
#         print(f"DB Company: {row['recall_company_name']}")
#         print(f"DB Product: {(row['product_description'] or '')[:100]}")
#         print(f"DB Raw Detail: {(row['raw_detail'] or '')[:100]}")

#         # --- BRAND SCORES ---
#         recall_brand = normalize(row["recall_brand_name"])
#         recall_company = normalize(row["recall_company_name"])
#         announcement = normalize(row["recall_announcement_text"])

#         brand_vs_brand = fuzz.token_set_ratio(brand_norm, recall_brand) if recall_brand else 0
#         brand_vs_company = fuzz.token_set_ratio(brand_norm, recall_company) if recall_company else 0
#         brand_vs_text = fuzz.partial_ratio(brand_norm, announcement) if announcement else 0
#         brand_score = max(brand_vs_brand, brand_vs_company, brand_vs_text)

#         print(f"\n  BRAND MATCHING:")
#         print(f"    vs brand_name     ({recall_brand[:50]}): {brand_vs_brand}")
#         print(f"    vs company_name   ({recall_company[:50]}): {brand_vs_company}")
#         print(f"    vs announcement   (partial_ratio): {brand_vs_text}")
#         print(f"    → Best brand score: {brand_score} {'✅ PASS' if brand_score >= 75 else '❌ FAIL (threshold: 75)'}")

#         # --- PRODUCT SCORES ---
#         recall_product = normalize(row["product_description"])
#         raw_detail = normalize(row["raw_detail"])
#         recall_title = normalize(row["recall_announcement_title"])

#         prod_vs_desc = fuzz.token_set_ratio(product_norm, recall_product) if recall_product else 0
#         prod_vs_raw = fuzz.token_set_ratio(product_norm, raw_detail) if raw_detail else 0
#         prod_vs_title = fuzz.token_set_ratio(product_norm, recall_title) if recall_title else 0
#         product_score = max(prod_vs_desc, prod_vs_raw, prod_vs_title)

#         print(f"\n  PRODUCT MATCHING:")
#         print(f"    vs product_desc   ({recall_product[:50]}): {prod_vs_desc}")
#         print(f"    vs raw_detail     ({raw_detail[:50]}): {prod_vs_raw}")
#         print(f"    vs title          ({recall_title[:50]}): {prod_vs_title}")
#         print(f"    → Best product score: {product_score} {'✅ PASS' if product_score >= 60 else '❌ FAIL (threshold: 60)'}")

#         # --- COMBINED ---
#         combined = round(brand_score * 0.4 + product_score * 0.6, 1)
#         match = brand_score >= 75 and product_score >= 60

#         print(f"\n  RESULT: {'🚨 MATCH' if match else '⛔ NO MATCH'} | Combined: {combined} | Brand: {brand_score} | Product: {product_score}")


# if __name__ == "__main__":
#     # --- CHANGE THESE TO TEST ---
#     brand = "hormel compleats"
#     product_name = "HORMEL COMPLEATS Chicken Breast & Gravy With Mashed Potatoes, 10 OZ"
#     # ----------------------------

#     debug_match(brand, product_name)


from rapidfuzz import fuzz

product = "rosina meatballs, italian style"
company = "rosina food products, inc."

print("partial_ratio:", fuzz.partial_ratio(company, product))
print("token_set_ratio:", fuzz.token_set_ratio(company, product))
print("partial_ratio reversed:", fuzz.partial_ratio(product, company))

filler = {"inc", "llc", "co", "corp", "company", "foods", "food", "products", "product", "enterprises", "group", "the", "of", "and"}
company = "rosina food products, inc."
words = [w for w in company.replace(",", "").replace(".", "").split() if w not in filler and len(w) > 2]
print(words)  # ['rosina']
print("rosina" in "rosina meatballs, italian style")  # True