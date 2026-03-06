import sqlite3
from rapidfuzz import fuzz

DB_PATH = "data/bitewise.db"

# Common filler words to strip from company names
FILLER = {
    "inc", "llc", "co", "corp", "corporation", "company", "foods", "food",
    "products", "product", "enterprises", "group", "the", "of", "and",
    "ltd", "limited", "dba", "usa", "us"
}


def load_recalls():
    """Load all active, non-Spanish recalls with their products"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            r.recall_id,
            r.recall_source,
            r.recall_announcement_title,
            r.recall_reason,
            r.recall_brand_name,
            r.recall_company_name,
            r.recall_url,
            r.recall_announcement_date,
            r.recall_publish_date,
            r.recall_risk_level,
            p.product_id,
            p.product_description,
            p.raw_detail
        FROM recalls r
        JOIN products p ON r.recall_id = p.recall_id
        WHERE r.is_recall_terminated = 0
        AND r.recall_announcement_title NOT LIKE '%Retira%'
        AND r.recall_announcement_title NOT LIKE '%Alerta%'
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def normalize(text):
    """Lowercase and collapse whitespace"""
    if not text:
        return ""
    return " ".join(text.lower().split())


def extract_key_words(text):
    """Extract meaningful words from a company/brand name"""
    if not text:
        return set()
    cleaned = text.replace(",", "").replace(".", "").replace("'", "").replace("&#039;", "")
    words = [w for w in cleaned.lower().split() if w not in FILLER and len(w) > 4]
    return set(words)


def brand_match(brand_norm, recall_brand, recall_company):
    """
    Match Instacart brand against recall brand/company.
    Returns score 0-100.

    Strategy:
    1. Direct fuzzy match against brand_name and company_name fields
    2. Extract key words from company name → check if any appear in brand
    3. Check if brand appears as substring in company or vice versa
    """
    if not brand_norm:
        return 0

    # Direct fuzzy match
    score_brand = fuzz.token_set_ratio(brand_norm, recall_brand) if recall_brand else 0
    score_company = fuzz.token_set_ratio(brand_norm, recall_company) if recall_company else 0

    # Key word match: "rosina" from "Rosina Food Products, Inc."
    company_words = extract_key_words(recall_company)
    brand_words = extract_key_words(recall_brand)
    all_key_words = company_words | brand_words

    keyword_score = 0
    for word in all_key_words:
        if word in brand_norm or brand_norm in word:
            keyword_score = 100
            break

    # Substring check: "chips ahoy" in "chips ahoy!" or vice versa
    substring_score = 0
    if recall_brand and (brand_norm in recall_brand or recall_brand in brand_norm):
        substring_score = 95
    if recall_company and (brand_norm in recall_company or recall_company in brand_norm):
        substring_score = max(substring_score, 90)

    return max(score_brand, score_company, keyword_score, substring_score)


def product_match(product_norm, recall_product, raw_detail, recall_title):
    """
    Match Instacart product name against recall product fields.
    Returns score 0-100.

    Strategy:
    1. token_set_ratio against product_description (best for reordered words)
    2. token_set_ratio against raw_detail (may have more info)
    3. token_set_ratio against announcement title (contains product info)
    """
    score_desc = fuzz.token_set_ratio(product_norm, recall_product) if recall_product else 0
    score_raw = fuzz.token_set_ratio(product_norm, raw_detail) if raw_detail else 0
    score_title = fuzz.token_set_ratio(product_norm, recall_title) if recall_title else 0

    return max(score_desc, score_raw, score_title)


def match_product(brand, product_name, size=None, brand_threshold=75, product_threshold=60):
    """
    Match an Instacart product against the recall database.

    Tier 1: Brand match (brand vs recall_brand_name + recall_company_name)
            → Must pass brand_threshold to continue
    Tier 2: Product match (product_name vs product_description + raw_detail + title)
            → If passes product_threshold → "high" match
            → If brand passed but product didn't → "warning" match

    Returns list of matches sorted by score, deduplicated by recall_id.
    """
    recalls = load_recalls()
    brand_norm = normalize(brand)
    product_norm = normalize(product_name)
    matches = []

    for row in recalls:
        recall_brand = normalize(row["recall_brand_name"])
        recall_company = normalize(row["recall_company_name"])
        recall_product = normalize(row["product_description"])
        raw_detail = normalize(row["raw_detail"])
        recall_title = normalize(row["recall_announcement_title"])

        # Tier 1: Brand match
        b_score = brand_match(brand_norm, recall_brand, recall_company)

        if b_score < brand_threshold:
            continue

        # Tier 2: Product match
        p_score = product_match(product_norm, recall_product, raw_detail, recall_title)

        # Categorize
        if p_score >= product_threshold:
            match_level = "high"
        else:
            match_level = "warning"

        combined_score = round(b_score * 0.4 + p_score * 0.6, 1)

        matches.append({
            "recall_id": row["recall_id"],
            "score": combined_score,
            "brand_score": b_score,
            "product_score": p_score,
            "match_level": match_level,
            "recall_source": row["recall_source"],
            "recall_announcement_title": row["recall_announcement_title"],
            "recall_reason": row["recall_reason"],
            "recall_company_name": row["recall_company_name"],
            "recall_brand_name": row["recall_brand_name"],
            "recall_url": row["recall_url"],
            "recall_date": row["recall_announcement_date"] or row["recall_publish_date"],
            "recall_risk_level": row["recall_risk_level"],
            "product_description": row["product_description"],
        })

    # Deduplicate: keep highest score per recall_id
    seen = {}
    for m in matches:
        rid = m["recall_id"]
        if rid not in seen or m["score"] > seen[rid]["score"]:
            seen[rid] = m

    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


if __name__ == "__main__":
    test_cases = [
        ("rosina", "Rosina Meatballs, Italian Style"),
        ("olympia provisions", "Olympia Provisions Bratwurst Sausage"),
        ("great value", "Great Value 4% Milkfat Minimum Small Curd Cottage Cheese"),
        ("prego", "Prego Marinara Sauce"),
        ("janes", "Janes Fu Zhou Fish Ball"),
        ("tippy toes", "Tippy Toes Banana Blueberry Apple Oat Organic Baby Food"),
        ("chips ahoy!", "Chips Ahoy! Baked Bites, Blondie"),
        ("spring & mulberry", "Spring & Mulberry Mint Leaf, Date Sweetened, 72% Dark Chocolate"),
        ("true sea moss", "True Sea Moss Strawberry Sea Moss Gel Superfood"),
        ("forward farms", "Forward Farms 85% Lean/15% Fat Ground Beef"),
        ("hormel compleats", "HORMEL COMPLEATS Chicken Breast & Gravy With Mashed Potatoes, 10 OZ"),
        ("golden island", "Golden Island Pork Snack Bites, Korean Barbecue, 1.5 oz, 12 ct"),
    ]

    for brand, product in test_cases:
        print(f"\n--- {brand} / {product} ---")
        results = match_product(brand, product)
        if results:
            for r in results[:3]:
                print(f"  [{r['match_level'].upper()}] Score: {r['score']} (brand: {r['brand_score']}, product: {r['product_score']})")
                print(f"  {r['recall_source']}: {r['recall_announcement_title'][:80]}...")
        else:
            print("  No matches found")