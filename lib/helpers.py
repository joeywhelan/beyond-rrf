import copy
import time

import pandas as pd
from elasticsearch import helpers


def create_index(client, index_name="hand_tools"):
    """Delete if exists, then create index with full mapping."""
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        print(f"Deleted existing index '{index_name}'")

    mapping = {
        "mappings": {
            "properties": {
                "product_id":     {"type": "keyword"},
                "name":           {"type": "text", "analyzer": "english"},
                "description":    {"type": "text", "analyzer": "english"},
                "description_semantic": {
                    "type": "semantic_text",
                    "inference_id": ".jina-embeddings-v5-text-small",
                },
                "category":       {"type": "keyword"},
                "brand":          {"type": "keyword"},
                "price":          {"type": "float"},
                "avg_rating":     {"type": "float"},
                "units_sold_30d": {"type": "integer"},
                "in_stock":       {"type": "boolean"},
            }
        }
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"Created index '{index_name}'")


def ingest_products(client, products, index_name="hand_tools"):
    """Bulk index products, stripping trap_for field."""
    docs = copy.deepcopy(products)
    actions = []
    for doc in docs:
        doc.pop("trap_for", None)
        doc["description_semantic"] = doc.get("description", "")
        actions.append({
            "_index": index_name,
            "_id": doc.get("product_id"),
            "_source": doc,
        })

    success, errors = helpers.bulk(client, actions)
    print(f"Indexed {success} documents into '{index_name}'")
    if errors:
        print(f"Errors: {errors}")

def display_results(hits, fields=None):
    """Return a DataFrame from a list of ES hits, including _score."""
    if fields is None:
        fields = ["name", "avg_rating", "units_sold_30d", "price"]

    rows = []
    for hit in hits:
        row = {"_score": hit["_score"]}
        for f in fields:
            row[f] = hit["_source"].get(f)
        rows.append(row)

    return pd.DataFrame(rows)


def side_by_side(frames, on="name", sort_by=None):
    """Merge multiple result DataFrames on product name for comparison."""
    result = None
    score_cols = []
    for key, df in frames.items():
        col = f"{key}_score"
        score_cols.append(col)
        scores = df[[on, "_score"]].rename(columns={"_score": col})
        if result is None:
            result = scores
        else:
            result = result.merge(scores, on=on, how="outer")
    sort_col = sort_by if sort_by and sort_by in result.columns else score_cols[0]
    result = result.sort_values(sort_col, ascending=False, na_position="last")
    result[score_cols] = result[score_cols].fillna("—")
    return result.reset_index(drop=True)
