import sqlite3
import os
import re
from datetime import date, datetime
from rapidfuzz import fuzz

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "data", "bitewise.db")
MAX_RECALL_AGE_DAYS = 180
GENERIC_PRODUCT_WORDS = {
    "all",
    "apple",
    "baked",
    "barbecue",
    "beef",
    "bite",
    "bites",
    "breast",
    "chicken",
    "chunk",
    "chunks",
    "classic",
    "curd",
    "dark",
    "fat",
    "food",
    "foods",
    "fresh",
    "frozen",
    "gel",
    "grass",
    "ground",
    "lean",
    "leaf",
    "marinara",
    "meat",
    "meatball",
    "meatballs",
    "milkfat",
    "mint",
    "natural",
    "organic",
    "pork",
    "potatoes",
    "pouch",
    "product",
    "products",
    "sauce",
    "sausage",
    "sea",
    "signature",
    "small",
    "snack",
    "snacks",
    "style",
    "superfood",
    "sweetened",
    "toes",
    "true",
    "value",
}
PROTEIN_CONFLICT_GROUPS = [
    {"beef", "pork", "chicken", "turkey", "fish", "shrimp"},
]
COMPANY_FILLER_WORDS = {
    "and",
    "co",
    "company",
    "corp",
    "corporation",
    "enterprises",
    "food",
    "foods",
    "group",
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "of",
    "product",
    "products",
    "the",
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
    if not text:
        return ""
    return " ".join(text.lower().split())


def tokenize(text):
    return re.findall(r"[a-z0-9]+", normalize(text))


def distinctive_tokens(text):
    return {
        token for token in tokenize(text)
        if len(token) > 2 and token not in GENERIC_PRODUCT_WORDS and not token.isdigit()
    }


def shared_distinctive_tokens(*texts):
    token_sets = [distinctive_tokens(text) for text in texts if text]
    if not token_sets:
        return set()
    shared = set()
    base = token_sets[0]
    for candidate in token_sets[1:]:
        shared.update(base & candidate)
    return shared


def extract_size_tokens(text):
    if not text:
        return set()
    matches = re.findall(r"\b\d+(?:\.\d+)?\s?(?:oz|ounce|ounces|lb|lbs|pound|pounds|g|gram|grams|kg|count|ct)\b", normalize(text))
    return {match.replace(" ", "") for match in matches}


def size_compatible(query_size, *candidate_texts):
    query_sizes = extract_size_tokens(query_size)
    if not query_sizes:
        return True

    candidate_sizes = set()
    for text in candidate_texts:
        candidate_sizes.update(extract_size_tokens(text))

    if not candidate_sizes:
        return True

    return bool(query_sizes & candidate_sizes)


def has_conflicting_distinctive_tokens(product_text, recall_text):
    product_tokens = set(tokenize(product_text))
    recall_tokens = set(tokenize(recall_text))

    for group in PROTEIN_CONFLICT_GROUPS:
        product_group = product_tokens & group
        recall_group = recall_tokens & group
        if product_group and recall_group and product_group != recall_group:
            return True

    return False


def parse_recall_date(date_str):
    """Parse ISO-like recall dates into a date object."""
    if not date_str:
        return None

    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def get_recall_age_days(recall_date_str):
    parsed_date = parse_recall_date(recall_date_str)
    if not parsed_date:
        return None
    return (date.today() - parsed_date).days


def simplify_company_name(text):
    """Reduce company names to their distinctive brand-like tokens."""
    normalized = normalize(text).replace(",", " ").replace(".", " ")
    parts = [part for part in normalized.split() if part not in COMPANY_FILLER_WORDS and len(part) > 2]
    return " ".join(parts)


def hybrid_brand_score(brand, target):
    """
    Hybrid brand matching score.
    Blends multiple fuzzy signals with a length penalty.

    - ratio: strict character-by-character similarity
    - token_sort_ratio: handles word reordering
    - partial_ratio: finds best substring match
    - len_ratio: penalizes when strings are very different lengths

    This prevents short generic words like "signature" from
    matching long brand names like "kirkland signature".
    """
    if not brand or not target:
        return 0

    exact = fuzz.ratio(brand, target)
    sorted_score = fuzz.token_sort_ratio(brand, target)
    partial = fuzz.partial_ratio(brand, target)
    len_ratio = min(len(brand), len(target)) / max(len(brand), len(target))

    score = (exact * 0.3) + (sorted_score * 0.3) + (partial * 0.2) + (len_ratio * 100 * 0.2)
    return score


def hybrid_product_score(product, target):
    """
    Hybrid product matching score.
    More forgiving than brand matching since product names
    vary wildly between retailer and recall descriptions.

    - token_set_ratio: ignores word order and extra words (best for products)
    - token_sort_ratio: rewards same words in any order
    - partial_ratio: finds substring matches
    """
    if not product or not target:
        return 0

    set_score = fuzz.token_set_ratio(product, target)
    sorted_score = fuzz.token_sort_ratio(product, target)
    partial = fuzz.partial_ratio(product, target)

    score = (set_score * 0.4) + (sorted_score * 0.35) + (partial * 0.25)
    return score


def brand_match(brand_norm, recall_brand, recall_company):
    """
    Match Instacart brand against recall brand and company name.
    Returns the best score from both comparisons.
    """
    score_brand = hybrid_brand_score(brand_norm, recall_brand)
    score_company = hybrid_brand_score(brand_norm, recall_company)
    simplified_company = simplify_company_name(recall_company)
    score_company_simplified = hybrid_brand_score(brand_norm, simplified_company)
    return max(score_brand, score_company, score_company_simplified)


def brand_match_details(brand_norm, recall_brand, recall_company):
    exact_brand_tokens = set(tokenize(brand_norm)) & set(tokenize(recall_brand))
    exact_company_tokens = set(tokenize(brand_norm)) & set(tokenize(simplify_company_name(recall_company)))

    score_brand = hybrid_brand_score(brand_norm, recall_brand)
    score_company = hybrid_brand_score(brand_norm, recall_company)
    score_company_simplified = hybrid_brand_score(brand_norm, simplify_company_name(recall_company))

    return {
        "score_brand": score_brand,
        "score_company": score_company,
        "score_company_simplified": score_company_simplified,
        "best_score": max(score_brand, score_company, score_company_simplified),
        "brand_token_overlap": exact_brand_tokens,
        "company_token_overlap": exact_company_tokens,
        "brand_exact": bool(exact_brand_tokens),
        "company_only": not exact_brand_tokens and bool(exact_company_tokens),
    }


def product_match(product_norm, brand_norm, recall_product, raw_detail, recall_title):
    """
    Match Instacart product name against recall product fields.
    Strips brand from product name first to avoid inflated scores.
    """
    # Remove brand name from product to compare just the product part
    product_clean = product_norm.replace(brand_norm, "").strip() if brand_norm else product_norm

    score_desc = hybrid_product_score(product_clean, recall_product)
    score_raw = hybrid_product_score(product_clean, raw_detail)
    score_title = hybrid_product_score(product_clean, recall_title)

    return max(score_desc, score_raw, score_title)


def product_match_details(product_norm, brand_norm, recall_product, raw_detail, recall_title):
    product_clean = product_norm.replace(brand_norm, "").strip() if brand_norm else product_norm
    score_desc = hybrid_product_score(product_clean, recall_product)
    score_raw = hybrid_product_score(product_clean, raw_detail)
    score_title = hybrid_product_score(product_clean, recall_title)

    candidates = {
        "product_description": (score_desc, recall_product),
        "raw_detail": (score_raw, raw_detail),
        "recall_title": (score_title, recall_title),
    }
    best_field, (best_score, best_text) = max(candidates.items(), key=lambda item: item[1][0])

    return {
        "product_clean": product_clean,
        "best_score": best_score,
        "best_field": best_field,
        "best_text": best_text,
        "shared_tokens": shared_distinctive_tokens(product_clean, recall_product, raw_detail, recall_title),
    }


def match_product(brand, product_name, size=None, brand_threshold=75, product_threshold=60):
    """
    Match an Instacart product against the recall database.

    Tier 1: Brand match → must pass brand_threshold
    Tier 2: Product match
            → passes product_threshold → "high"
            → brand passed but product didn't → "warning"

    Returns list of matches sorted by score, deduplicated by recall_id.
    """
    recalls = load_recalls()
    brand_norm = normalize(brand)
    product_norm = normalize(product_name)
    matches = []

    for row in recalls:
        recall_date = row["recall_announcement_date"] or row["recall_publish_date"]
        recall_age_days = get_recall_age_days(recall_date)

        if recall_age_days is None or recall_age_days > MAX_RECALL_AGE_DAYS:
            continue

        recall_brand = normalize(row["recall_brand_name"])
        recall_company = normalize(row["recall_company_name"])
        recall_product = normalize(row["product_description"])
        raw_detail = normalize(row["raw_detail"])
        recall_title = normalize(row["recall_announcement_title"])

        # Tier 1: Brand match
        brand_details = brand_match_details(brand_norm, recall_brand, recall_company)
        b_score = brand_details["best_score"]

        if b_score < brand_threshold:
            continue

        if brand_details["company_only"] and b_score < 88:
            continue

        # Tier 2: Product match
        product_details = product_match_details(product_norm, brand_norm, recall_product, raw_detail, recall_title)
        p_score = product_details["best_score"]

        if not product_details["shared_tokens"] and p_score < 85:
            continue

        if has_conflicting_distinctive_tokens(product_details["product_clean"], product_details["best_text"]):
            continue

        if not size_compatible(size, recall_product, raw_detail, recall_title):
            continue

        # Categorize
        if p_score >= max(product_threshold, 68) and product_details["shared_tokens"] and not brand_details["company_only"]:
            match_level = "high"
        else:
            match_level = "warning"

        combined_score = round(b_score * 0.4 + p_score * 0.6, 1)

        matches.append({
            "recall_id": row["recall_id"],
            "score": combined_score,
            "brand_score": round(b_score, 1),
            "product_score": round(p_score, 1),
            "match_level": match_level,
            "shared_product_tokens": sorted(product_details["shared_tokens"]),
            "recall_source": row["recall_source"],
            "recall_announcement_title": row["recall_announcement_title"],
            "recall_reason": row["recall_reason"],
            "recall_company_name": row["recall_company_name"],
            "recall_brand_name": row["recall_brand_name"],
            "recall_url": row["recall_url"],
            "recall_date": recall_date,
            "recall_age_days": recall_age_days,
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
        ("kirkland signature", "Kirkland Signature Grass-Fed Beef Sticks, 1.15 oz, 12 ct")
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
