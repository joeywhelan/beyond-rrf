# Plan: HTML Presentation — Beyond Rank Fusion

## Context

The repo contains a Jupyter notebook (`demo.ipynb`) and narrative article (`assets/article.md`) demonstrating Elasticsearch hybrid search retrievers (RRF, Linear, Rescorer). The goal is a standalone HTML slide deck targeting IT management and engineers — technical but not code-level. It should clearly communicate Elastic's hybrid search capabilities and use Elastic's brand colors.

## Approach

Generate a single self-contained HTML file (`presentation.html`) at the repo root using [reveal.js](https://revealjs.com/) loaded from CDN. All styles inline — no build step required. Open in any browser.

## Elastic Brand Colors

- Primary: `#07C` (Elastic blue)
- Dark background: `#1B1B3A` (dark navy)
- Accent: `#00BFB3` (teal/green)
- Text: `#FFFFFF` on dark backgrounds
- Secondary text: `#98A2B3`
- Slide titles: Elastic blue or white

## Slide Outline (14 slides)

| # | Slide | Content |
|---|-------|---------|
| 1 | **Title** | "Beyond Rank Fusion: A Practical Guide to Elasticsearch Retrievers" + subtitle + cover image |
| 2 | **Agenda** | What we'll cover — 5 bullet points from article's "What This Article Covers" (without Terraform detail) |
| 3 | **Architecture** | Embed `assets/arch.png` + 3–4 bullet flow summary |
| 4 | **Dataset** | 80 hand tools, business signals (rating, sales, stock), "trap" products to stress-test retrievers — sample JSON (simplified) |
| 5 | **Baseline: Lexical vs Semantic** | Side-by-side explanation of BM25 vs semantic + `assets/scenario-1.png` |
| 6 | **How RRF Works** | Conceptual explanation — rank-based fusion, no score awareness, `rank_constant` parameter. Formula: `1 / (rank + k)` |
| 7 | **RRF Results** | `assets/scenario-2.png` + key findings: keyword stuffing persists, Trap A1 stays #1, A2 invisible. Takeaway bullet. |
| 8 | **How Linear Works** | Score-based fusion with MinMax normalization — magnitude matters. Conceptual comparison vs RRF. |
| 9 | **Linear Results** | `assets/scenario-3.png` + key findings: Mortise Chisel dominance expressed, Pigsticker exposed, weight dial has real effect. |
| 10 | **How Rescorer Works** | Wraps Linear, injects business signals (ratings, sales, stock). Conceptual formula explanation (no code). |
| 11 | **Rescorer Results** | `assets/scenario-4.png` + row-by-row highlights: Estwing vaults to #1, Reliable Claw drops out, Lie-Nielsen killed by `in_stock: false`. |
| 12 | **Decision Matrix** | When to use each retriever — comparison table from article summary section |
| 13 | **Key Takeaways** | 3–4 crisp bullets: hybrid != automatic quality, score magnitude matters, business logic is the final layer |
| 14 | **Resources** | GitHub link, Elastic docs links for each retriever type |

## Technical Details

- **Framework:** reveal.js 5.x via CDN (`https://cdn.jsdelivr.net/npm/reveal.js@5/`)
- **Single file:** `presentation.html` — all CSS overrides in `<style>`, reveal.js + plugins loaded from CDN
- **Images:** Referenced as relative paths (`assets/arch.png`, `assets/scenario-*.png`, `assets/cover600x322.png`)
- **Responsive images:** `max-width: 90%; max-height: 60vh` so scenario screenshots fit without overflow
- **Fragment animations:** Use reveal.js fragments for bullet-point build where appropriate (e.g., decision matrix rows)
- **Navigation:** Standard reveal.js arrows + keyboard. No vertical slides — keep it linear.
- **Speaker notes:** Include brief speaker notes on key slides via `<aside class="notes">`

## Files to Create

| File | Purpose |
|------|---------|
| `presentation.html` | The complete self-contained slide deck |

## Files Referenced (read-only)

| File | Used for |
|------|----------|
| `assets/article.md` | Narrative content, takeaways, decision matrix |
| `assets/arch.png` | Architecture diagram slide |
| `assets/cover600x322.png` | Title slide image |
| `assets/scenario-1.png` | Baseline results |
| `assets/scenario-2.png` | RRF results |
| `assets/scenario-3.png` | Linear results |
| `assets/scenario-4.png` | Rescorer results |

## Verification

1. Open `presentation.html` in a browser
2. Confirm all 14 slides render with correct content
3. Confirm all images load (arch.png, scenario-1 through 4, cover)
4. Confirm Elastic color scheme is applied (dark navy background, blue/teal accents)
5. Confirm arrow-key navigation works
6. Confirm text is readable and images are properly sized on a standard 16:9 display
