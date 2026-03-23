# Plan: Elastic Hybrid Search Retriever Notebook
## Progressive Arc: BM25 & Semantic → RRF → Linear → Rescorer

---

## Overview

This notebook demonstrates the escalating capabilities of Elastic hybrid search
retrievers using a hand tools product catalog. Each section introduces a new
retriever that solves a problem the previous one cannot. The dataset is
pre-engineered with deliberate "trap" documents that expose each retriever's
limitations, motivating the transition to the next.

**Elastic infrastructure is provisioned via Terraform** directly from the
notebook. The notebook creates a `.env` file from Terraform outputs containing
`ELASTIC_CLOUD_ID`, `ELASTIC_USERNAME`, and `ELASTIC_PASSWORD`.

---

## Tech Stack

- Python 3.10+
- `elasticsearch` Python client (9.x)
- Embeddings via **Jina Embeddings v5** hosted on the **Elastic Inference Service (EIS)** —
  no local model or `sentence-transformers` required. The inference endpoint
  `.jina-embeddings-v5-text-small` (note the leading dot — a reserved/preconfigured
  EIS endpoint) is automatically available on Elastic Serverless.
- `pandas` — result display and comparison tables
- `jupyter` / `jupyterlab`
- `python-dotenv` — environment variable loading
- Dataset: hand-crafted JSON file (`products.json`) — **not generated at
  runtime**. Checked in alongside the notebook.

---

## Repository Structure

```
hybrid-es/
├── plan_code.md              ← this file
├── demo.ipynb                ← the Jupyter notebook
├── data/
│   └── products.json         ← static hand tools product catalog (see Dataset section)
├── lib/
│   └── helpers.py            ← index creation, ingestion, display utilities
├── terraform/
│   └── ...                   ← Elastic Serverless provisioning
└── requirements.txt
```

---

## Section 1 — Environment Setup

**Notebook cells:**

1. Install dependencies from `requirements.txt`.
2. Provision Elastic Serverless via Terraform (`terraform init` + `terraform apply`).
3. Create `.env` from Terraform outputs (`ELASTIC_USERNAME`, `ELASTIC_PASSWORD`, `ELASTIC_CLOUD_ID`).
4. Import dependencies (`elasticsearch`, `pandas`, helpers from `lib/helpers.py`).
5. Load env vars with `python-dotenv` and instantiate the `Elasticsearch` client.
6. Load `data/products.json` into a Python list. Print record count (expect 80).
7. Create the `hand_tools` index via `create_index(client)`.
8. Ingest products via `ingest_products(client, products)`.

---

## Section 2 — Baseline: BM25 vs Semantic

**Purpose:** Establish that neither retrieval method alone is sufficient.

**Query:** `"versatile fastening tool for woodworking joints"`

**Cells:**

1. Run a `multi_match` BM25 query against `name` and `description`. Display top 7
   results with name, `_score`, `avg_rating`, `units_sold_30d`, `price`.
2. Run a `semantic` query against `description_semantic`. Display top 7.

**Narrative callout:**
> BM25 rewards exact keyword overlap — "fastening" and "woodworking" score well.
> The semantic query uses Jina Embeddings via EIS to find meaning beyond the
> words — it may surface products that never use the word "fastening" but are
> conceptually relevant. Neither is wrong. The challenge is combining them
> intelligently.

---

## Section 3 — RRF Retriever (Unweighted then Weighted)

**Query:** `"precision screwdriver for electronics repair"`

**Cells:**

1. **Unweighted RRF**: Standard retriever (BM25 on `name`+`description`) +
   standard retriever (semantic query on `description_semantic`).
   `rank_window_size: 50`. Display top 7.
2. Markdown callout: point out Trap A1 (keyword-stuffed, #1) and Trap A2
   (semantically ideal, absent from results). Explain why using rank arithmetic.
3. **Weighted RRF — BM25 boosted**: BM25 retriever at `weight: 2.0`. Display top 7.
4. **Weighted RRF — semantic boosted**: Semantic retriever at `weight: 2.0`. Display top 7.
5. Side-by-side DataFrame: unweighted vs BM25-boosted vs semantic-boosted.

**Key observations from actual results:**
- A1 (PrecisionDrive) is #1 across all three columns — keyword stuffing games both retrievers
- A2 (Vessel Impacta) is absent from unweighted and BM25-boosted, only appears at #7 under semantic boost
- A3 (Wiha) is #2 in every column but can never overtake A1
- Mitutoyo (caliper) appears in unweighted and BM25-boosted but drops under semantic boost
- Knipex (pliers) appears in all three columns near the bottom

**Narrative callout:**
> Weighted RRF gives you a dial — but the dial only adjusts how much each
> retriever's *rank position* counts. A1 stays at #1 regardless of weighting
> because it games both legs. RRF has no way to penalise shallow, keyword-stuffed
> content — it cannot tell whether rank 1 was a near-perfect match or barely
> squeaked past rank 2. We need score magnitudes and business signals.

---

## Section 4 — Linear Retriever

**Query:** `"mortise chisel for hand-cut joinery"`

**Cells:**

1. **RRF baseline** for this query — establishes the rank-based ordering.
2. **Linear retriever — semantic-heavy**: MinMax normalization, BM25 `weight: 0.3`,
   semantic `weight: 0.7`. Display top 7.
3. **Linear retriever — BM25-heavy**: MinMax normalization, BM25 `weight: 0.6`,
   semantic `weight: 0.4`. Display top 7.
4. Side-by-side DataFrame: RRF vs Linear (BM25-heavy) vs Linear (semantic-heavy).

**Key observations from actual results:**
- Mortise Chisel scores 1.0 in both Linear columns — MinMax maps it to the ceiling
- Pigsticker appears in both Linear columns but not RRF; Firmer Chisel is the reverse
- Narex vs Pigsticker: BM25-heavy has Pigsticker (0.20) competitive with Narex (0.27);
  semantic-heavy collapses Pigsticker to 0.10 while Narex rises to 0.30

**Narrative callout:**
> Linear sees the *magnitude* of scores, not just their rank. When the Mortise
> Chisel scores 52 on BM25 and the next product scores 11, Linear respects that
> gap — RRF does not. The weight dial now has real teeth. But Linear still
> operates purely on retrieval scores — it has no idea what `avg_rating` or
> `units_sold_30d` are. For that, we need the Rescorer.

---

## Section 5 — Rescorer Retriever

**Query:** `"reliable claw hammer for general carpentry"`

The Rescorer wraps a first-stage Linear retriever and applies a rescore query:
```
final = query_weight * linear_score + rescore_query_weight * rescore_score
```
Where `rescore_score = linear_score * log1p(units_sold_30d) * (avg_rating / 5.0)`.

With `query_weight: 1, rescore_query_weight: 2`, this blends relevance with
business signals — relevance still matters, but products with strong sales and
ratings get a significant boost.

**Cells:**

1. **Linear baseline** (no rescoring). BM25 0.6 / semantic 0.4 with MinMax. Display top 7.
2. **Rescorer** wrapping Linear, `query_weight: 1, rescore_query_weight: 2`,
   `window_size: 50`. Display top 7.
3. **Rescorer + in_stock penalty**: Extends the script to multiply by
   `doc['in_stock'].value ? 1.0 : 0.1`. Display top 7.
4. **Score breakdown**: Shows the math behind rescoring — linear_score,
   rating_mult, velocity_mult, stock_mult, and final scores.
5. Side-by-side DataFrame: Linear vs Rescorer vs Rescorer+stock.

**Key observations from actual results:**
- Reliable Claw Hammer: Linear #1 (0.98) but drops out of rescorer top 7 (rating 1.9, 14 sold)
- Estwing: Linear #7 (0.07) → Rescorer #1 (14.88) thanks to rating 4.9 and 1840 sold
- Lie-Nielsen: Linear #2 (0.84) → Rescorer #2 (11.87) → Rescorer+stock "—" (in_stock: false)

**Narrative callout:**
> The Rescorer doesn't change what gets *retrieved* — it changes what gets
> *promoted*. The Lie-Nielsen hammer ranks #2 in the linear baseline and earns a
> strong rescorer score — but vanishes from rescorer+stock because `in_stock` is
> `false`. One boolean field overrides all relevance and popularity signals.

---

## Section 6 — Summary & Comparison

**Cells:**

1. Markdown table summarising the retriever configurations:

| Retriever          | Fusion method       | Score magnitude? | Weights? | Post-retrieval business logic? |
|--------------------|---------------------|------------------|----------|-------------------------------|
| RRF (unweighted)   | Rank-based          | No               | No       | No                            |
| RRF (weighted)     | Rank-based          | No               | Yes      | No                            |
| Linear + MinMax    | Score-based         | Yes              | Yes      | No                            |
| Rescorer           | Score-based + rerank| Yes              | Yes      | **Yes**                       |

2. Run all four retriever configurations against a single query:
   `"durable hand tool for precise woodworking"`. Display top 5 from each
   side-by-side. The Rescorer uses `rank_window_size: 5` and `window_size: 5`
   so it re-ranks within the same candidate pool as Linear (no new products
   introduced).
3. Final markdown narrative: when to reach for each retriever.

---

## Teardown

Destroy the Elastic Serverless environment via `terraform destroy`.

---

## Dataset Design (`data/products.json`)

### General Corpus

80 total products across these categories:

| Category              | Count |
|-----------------------|-------|
| Hammers & Mallets     | 15    |
| Screwdrivers & Bits   | 14    |
| Planes & Chisels      | 12    |
| Clamps & Vises        | 9     |
| Saws (hand)           | 8     |
| Measuring & Layout    | 8     |
| Wrenches & Pliers     | 8     |
| Drills & Braces       | 6     |

Descriptions use a mix of exact trade terms and semantic synonyms to create
meaningful BM25/semantic divergence.

---

### Trap Documents (14 — embedded in the general corpus)

Each trap document includes a `"trap_for"` string field in the JSON for
documentation purposes. This field is **not** added to the Elasticsearch mapping
and is removed during ingestion.

---

#### Trap Set A — Section 3 (RRF demo)

**Query:** `"precision screwdriver for electronics repair"`

- **Trap A1** `"trap_for": "weighted_rrf_bm25_strong_knn_weak"`:
  Keyword-stuffed screwdriver set. BM25 scores very highly due to repeated
  "precision screwdriver" and "electronics repair" terms. Modern embedding models
  extract meaning even from keyword-stuffed text, so it also ranks well semantically.
  ```
  name: "PrecisionDrive 6-Piece Screwdriver Set"
  description: "Precision screwdriver set for electronics repair. Precision-ground
    tips on precision handles with precision grip zones. Each precision screwdriver
    is magnetised for precision fastener control. Precision electronics repair toolkit."
  avg_rating: 3.6, units_sold_30d: 95, price: 34.99
  ```
  *Games both BM25 and semantic legs → #1 in all RRF variants.*

- **Trap A2** `"trap_for": "weighted_rrf_knn_strong_bm25_weak"`:
  A screwdriver with a rich semantic description of electronics repair work
  but zero query keywords ("precision", "screwdriver", "electronics", "repair"
  all absent).
  ```
  name: "Vessel Impacta No.2 JIS Driver"
  description: "Favoured by technicians for delicate board-level rework and
    micro-soldering on compact devices. Seats firmly in Japanese Industrial
    Standard recesses without cam-out. The slim barrel allows sustained control
    when swapping tiny components on densely packed circuit boards, reflowing
    solder joints, and navigating cramped enclosures. A quiet favourite in
    repair shops that service portable gadgets."
  avg_rating: 4.8, units_sold_30d: 410, price: 18.50
  ```
  *BM25: invisible. Semantic: strong. RRF without semantic boost: absent.
  Only appears at #7 when semantic retriever is boosted to weight 2.0.*

- **Trap A3** `"trap_for": "weighted_rrf_control"`:
  Genuinely relevant product that should rank high.
  ```
  name: "Wiha Precision Micro Screwdriver Set"
  avg_rating: 4.6, units_sold_30d: 280, price: 42.99
  ```
  *#2 in all RRF variants — can never overtake keyword-stuffed A1.*

- **Trap A4** `"trap_for": "weighted_rrf_distractor"`:
  General-purpose screwdriver set not related to electronics repair.
  ```
  name: "Wera Kraftform Big Pack 300 Screwdriver Set"
  avg_rating: 4.4, units_sold_30d: 350, price: 59.99
  ```

---

#### Trap Set B — Section 4 (Linear Retriever demo)

**Query:** `"mortise chisel for hand-cut joinery"`

- **Trap B1** `"trap_for": "linear_magnitude_dominant"`:
  Name and description saturated with exact query terms, creating a raw BM25
  score far above the field average (~52 vs ~11 for rank 2).
  ```
  name: "Mortise Chisel Heavy-Duty Hand Cut Joinery Chisel"
  avg_rating: 3.8, units_sold_30d: 140, price: 42.00
  ```
  *Scores 1.0 in both Linear columns (MinMax ceiling). RRF can't express
  this dominance — it just sees "rank 1."*

- **Trap B2** `"trap_for": "linear_magnitude_suppressed"`:
  Semantically rich mortise chisel description with moderate BM25 score.
  ```
  name: "Two Cherries 3/4" Pigsticker Oval-Bolster Mortise Chisel"
  avg_rating: 4.9, units_sold_30d: 88, price: 94.00
  ```
  *Appears in both Linear columns but not in RRF. BM25-heavy: 0.20,
  semantic-heavy: 0.10 — the gap reveals keyword vs semantic relevance.*

- **Trap B3** `"trap_for": "linear_magnitude_neither"`:
  Tangentially related woodworking vise.
  ```
  name: "Record 52-1/2 Quick-Release Woodworking Vise"
  avg_rating: 4.6, units_sold_30d: 210, price: 139.00
  ```

- **Trap B4** `"trap_for": "linear_control"`:
  ```
  name: "Narex Premium Bench Chisel 3/4-Inch"
  avg_rating: 4.3, units_sold_30d: 195, price: 28.00
  ```

- **Trap B5** `"trap_for": "linear_distractor"`:
  ```
  name: "Stanley No.4 Smoothing Plane"
  avg_rating: 4.1, units_sold_30d: 170, price: 65.00
  ```

---

#### Trap Set C — Section 5 (Rescorer demo)

**Query:** `"reliable claw hammer for general carpentry"`

- **Trap C1** `"trap_for": "rescorer_relevance_trap"`:
  Most keyword- and semantically-relevant result, but terrible business signals.
  ```
  name: "Reliable Claw Hammer General Carpentry 16oz"
  avg_rating: 1.9, units_sold_30d: 14, price: 22.99
  ```
  *Linear rank: 1 (score 0.98). After rescoring: drops out of top 7.*

- **Trap C2** `"trap_for": "rescorer_business_winner"`:
  Good but not exceptional relevance. Best-selling, highest-rated hammer.
  ```
  name: "Estwing E3-16C 16oz Curved Claw Hammer"
  avg_rating: 4.9, units_sold_30d: 1840, price: 37.99
  ```
  *Linear rank: 7 (score 0.07). After rescoring: rises to rank 1 (score 14.88).*

- **Trap C3** `"trap_for": "rescorer_middleground"`:
  Moderate relevance, middling business signals.
  ```
  name: "Stanley FatMax 20oz Framing Hammer"
  avg_rating: 4.2, units_sold_30d: 520, price: 44.99
  ```

- **Trap C4** `"trap_for": "rescorer_in_stock_filter"`:
  Strong relevance and business signals but out of stock.
  ```
  name: "Lie-Nielsen Warrington Pattern Hammer"
  description: "A reliable general carpentry hammer favoured by professionals
    for framing, trim work, and cabinet installation."
  avg_rating: 4.8, units_sold_30d: 310, price: 118.00, in_stock: false
  ```
  *Linear rank: 2 (score 0.84). Rescorer rank: 2 (score 11.87).
  Rescorer+stock: drops out entirely. The key demonstration of business
  logic that no retriever upstream can enforce.*

- **Trap C5** `"trap_for": "rescorer_filler"`:
  ```
  name: "Vaughan 999L 20oz Framing Rip Hammer"
  avg_rating: 4.0, units_sold_30d: 245, price: 32.99
  ```

---

## Index Mapping

Two fields carry the description content:
- `description` — `text` with `english` analyzer (supports BM25 `multi_match`)
- `description_semantic` — `semantic_text` with inference_id `.jina-embeddings-v5-text-small`
  (supports `semantic` queries, embeddings generated server-side by EIS)

During ingestion, `description_semantic` is populated with the same text as
`description`. This dual-field approach is necessary because `semantic_text`
does not support `match` or `multi_match` queries.

```json
{
  "mappings": {
    "properties": {
      "product_id":     { "type": "keyword" },
      "name":           { "type": "text", "analyzer": "english" },
      "description":    { "type": "text", "analyzer": "english" },
      "description_semantic": {
        "type": "semantic_text",
        "inference_id": ".jina-embeddings-v5-text-small"
      },
      "category":       { "type": "keyword" },
      "brand":          { "type": "keyword" },
      "price":          { "type": "float" },
      "avg_rating":     { "type": "float" },
      "units_sold_30d": { "type": "integer" },
      "in_stock":       { "type": "boolean" }
    }
  }
}
```

---

## `lib/helpers.py` — Function Signatures

```python
def create_index(client: Elasticsearch, index_name: str = "hand_tools") -> None:
    """Delete if exists, then create index with full mapping."""

def ingest_products(
    client: Elasticsearch,
    products: list[dict],
    index_name: str = "hand_tools"
) -> None:
    """
    Pop 'trap_for' field from each product before indexing.
    Copy 'description' into 'description_semantic' for dual-field search.
    Bulk index all documents.
    """

def display_results(hits: list, fields: list[str] = None) -> pd.DataFrame:
    """Return a DataFrame from a list of ES hits, including _score."""

def side_by_side(frames: dict[str, pd.DataFrame], on: str = "name",
                 sort_by: str = None) -> pd.DataFrame:
    """Merge multiple result DataFrames on product name for comparison."""
```

---

## `requirements.txt`

```
elasticsearch>=9.0.0
pandas>=2.0.0
jupyter>=1.0.0
python-dotenv>=1.0.0
python-terraform>=0.10.0
```

---

## Notes

- Do not auto-generate `products.json` with a language model or random data.
  The trap documents must be authored exactly as specified — the demo only works
  if the BM25/semantic divergence is real and predictable.
- The `description_semantic` field uses `semantic_text` backed by
  `.jina-embeddings-v5-text-small` on EIS. No client-side embedding logic needed.
- The `trap_for` field must be popped before bulk indexing — it is not in the mapping.
- All retriever queries use the `retriever` top-level key in the `_search` API.
  Do not use legacy `sub_searches` + `rank` syntax.
- Semantic sub-retrievers use a `standard` retriever wrapping a `semantic` query
  on `description_semantic` — not a `knn` retriever.
- Modern embedding models (like Jina v5) are robust to keyword stuffing — they
  extract meaning even from repetitive text. This is why Trap A1 games both
  BM25 and semantic, and the narrative embraces this finding rather than trying
  to work around it.
- The Rescorer uses `query_weight: 1, rescore_query_weight: 2` — a realistic
  blend where relevance still matters but business signals get double weight.
- The Section 6 comparison uses `rank_window_size: 5` and `window_size: 5` on
  the rescorer so it re-ranks within the same candidate pool as Linear, avoiding
  irrelevant products dominating via business signals alone.
