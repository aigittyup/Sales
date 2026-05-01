"""Business ontology and semantic classification for sales data."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class ColumnRole(str, Enum):
    DIMENSION = "dimension"    # Categorical grouping columns
    MEASURE = "measure"        # Numeric values to aggregate
    TEMPORAL = "temporal"      # Date / time columns
    IDENTIFIER = "identifier"  # ID / key columns
    TEXT = "text"              # Free-text columns


@dataclass
class OntologyTerm:
    """A concept in the sales business ontology."""

    name: str
    label: str
    description: str
    synonyms: list[str] = field(default_factory=list)
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "synonyms": self.synonyms,
            "parent": self.parent,
            "children": self.children,
            "properties": self.properties,
        }


@dataclass
class ColumnClassification:
    """Semantic classification of a single DataFrame column."""

    column: str
    role: ColumnRole
    ontology_term: str | None
    semantic_type: str
    relationships: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "role": self.role.value,
            "ontology_term": self.ontology_term,
            "semantic_type": self.semantic_type,
            "relationships": self.relationships,
        }


# ---------------------------------------------------------------------------
# Sales domain ontology terms
# ---------------------------------------------------------------------------

_SALES_TERMS: dict[str, OntologyTerm] = {
    "transaction": OntologyTerm(
        name="transaction",
        label="Sales Transaction",
        description="A single sales event capturing what was sold, where, and for how much.",
        synonyms=["sale", "order", "purchase", "deal"],
        children=["product", "region", "channel", "revenue", "quantity", "date", "customer"],
    ),
    "product": OntologyTerm(
        name="product",
        label="Product",
        description="A good or service offered for sale.",
        synonyms=["item", "sku", "good", "widget", "article"],
        parent="transaction",
        properties={"role": "dimension", "dimension_of": "transaction"},
    ),
    "region": OntologyTerm(
        name="region",
        label="Sales Region",
        description="Geographic area associated with a sale.",
        synonyms=["territory", "area", "geography", "location", "zone"],
        parent="transaction",
        children=["country", "state", "city"],
        properties={"role": "dimension", "dimension_of": "transaction", "has_hierarchy": True},
    ),
    "country": OntologyTerm(
        name="country",
        label="Country",
        description="Country of sale.",
        synonyms=["nation"],
        parent="region",
    ),
    "state": OntologyTerm(
        name="state",
        label="State / Province",
        description="State or province of sale.",
        synonyms=["province", "territory"],
        parent="region",
    ),
    "city": OntologyTerm(
        name="city",
        label="City",
        description="City of sale.",
        synonyms=["town", "municipality"],
        parent="region",
    ),
    "channel": OntologyTerm(
        name="channel",
        label="Sales Channel",
        description="Distribution channel through which the sale occurred.",
        synonyms=["distribution_channel", "sales_channel", "medium", "source"],
        parent="transaction",
        properties={"role": "dimension", "dimension_of": "transaction"},
    ),
    "revenue": OntologyTerm(
        name="revenue",
        label="Revenue",
        description="Total monetary value of a sale.",
        synonyms=["sales", "income", "amount", "price", "total", "value", "gmv"],
        parent="transaction",
        properties={"role": "measure", "measure_of": "transaction", "unit": "currency"},
    ),
    "quantity": OntologyTerm(
        name="quantity",
        label="Quantity Sold",
        description="Number of units sold in a transaction.",
        synonyms=["units", "qty", "count", "volume", "items", "pieces"],
        parent="transaction",
        properties={"role": "measure", "measure_of": "transaction", "unit": "units"},
    ),
    "date": OntologyTerm(
        name="date",
        label="Transaction Date",
        description="Date when the sale occurred.",
        synonyms=["order_date", "sale_date", "timestamp", "created_at", "transaction_date"],
        parent="transaction",
        properties={"role": "temporal"},
    ),
    "customer": OntologyTerm(
        name="customer",
        label="Customer",
        description="Entity that purchased the product.",
        synonyms=["buyer", "client", "account", "consumer"],
        parent="transaction",
        properties={"role": "dimension"},
    ),
    "category": OntologyTerm(
        name="category",
        label="Product Category",
        description="High-level grouping of products.",
        synonyms=["product_category", "type", "group", "segment"],
        parent="product",
        children=["subcategory"],
        properties={"role": "dimension", "has_hierarchy": True},
    ),
    "subcategory": OntologyTerm(
        name="subcategory",
        label="Product Subcategory",
        description="Finer grouping within a product category.",
        synonyms=["sub_category", "product_subcategory"],
        parent="category",
    ),
    "profit": OntologyTerm(
        name="profit",
        label="Profit",
        description="Revenue minus cost.",
        synonyms=["margin", "net_income", "earnings", "net_profit"],
        parent="transaction",
        properties={"role": "measure", "measure_of": "transaction", "unit": "currency"},
    ),
    "cost": OntologyTerm(
        name="cost",
        label="Cost of Goods Sold",
        description="Cost incurred to produce or acquire the sold item.",
        synonyms=["cogs", "cost_of_sales", "unit_cost", "expense"],
        parent="transaction",
        properties={"role": "measure", "measure_of": "transaction", "unit": "currency"},
    ),
    "discount": OntologyTerm(
        name="discount",
        label="Discount",
        description="Price reduction applied to the transaction.",
        synonyms=["reduction", "markdown", "promo", "rebate"],
        parent="transaction",
        properties={"role": "measure", "measure_of": "transaction"},
    ),
    "order_id": OntologyTerm(
        name="order_id",
        label="Order ID",
        description="Unique identifier for a sales transaction.",
        synonyms=["transaction_id", "sale_id", "order_number", "id", "key"],
        parent="transaction",
        properties={"role": "identifier"},
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _match_term(col_name: str) -> str | None:
    """Match a column name to the closest ontology term name."""
    col_lower = col_name.lower()
    if col_lower in _SALES_TERMS:
        return col_lower
    for term_name, term in _SALES_TERMS.items():
        all_names = [term_name] + term.synonyms
        if any(col_lower == s or s in col_lower or col_lower in s for s in all_names):
            return term_name
    return None


def _classify_role(col_name: str, dtype: str) -> ColumnRole:
    if "datetime" in dtype:
        return ColumnRole.TEMPORAL
    if pd.api.types.is_numeric_dtype(pd.Series(dtype=dtype)):
        return ColumnRole.MEASURE
    if any(k in col_name.lower() for k in ("id", "key", "code", "sku", "order_no", "order_id")):
        return ColumnRole.IDENTIFIER
    return ColumnRole.DIMENSION


def _infer_semantic_type(col_name: str, dtype: str) -> str:
    col_lower = col_name.lower()
    if "datetime" in dtype:
        return "datetime"
    if any(k in col_lower for k in ("revenue", "price", "cost", "profit", "amount", "discount", "value", "total")):
        return "currency"
    if any(k in col_lower for k in ("quantity", "qty", "units", "count", "num", "volume")):
        return "quantity"
    if any(k in col_lower for k in ("pct", "percent", "rate", "ratio", "share", "growth")):
        return "percentage"
    if any(k in col_lower for k in ("id", "key", "code", "sku")):
        return "identifier"
    if "date" in col_lower or "time" in col_lower:
        return "date"
    if dtype in ("object", "str", "string"):
        return "categorical"
    if "float" in dtype or "int" in dtype:
        return "numeric"
    return "unknown"


# ---------------------------------------------------------------------------
# Main ontology class
# ---------------------------------------------------------------------------

class SalesOntology:
    """Business ontology for the sales domain.

    Provides:
    - A catalog of known sales concepts and their relationships
    - Column classification (role, semantic type, ontology mapping)
    - Relationship inference between columns

    Usage:
        ontology = SalesOntology()
        classifications = ontology.classify_columns(df)
    """

    def __init__(self) -> None:
        self.terms: dict[str, OntologyTerm] = {k: v for k, v in _SALES_TERMS.items()}

    def classify_columns(self, df: pd.DataFrame) -> list[ColumnClassification]:
        """Classify every column in df by role, semantic type, and ontology term."""
        results: list[ColumnClassification] = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            role = _classify_role(col, dtype)
            term = _match_term(col)
            semantic_type = _infer_semantic_type(col, dtype)
            rels = self._infer_relationships(col, df)
            results.append(ColumnClassification(
                column=col,
                role=role,
                ontology_term=term,
                semantic_type=semantic_type,
                relationships=rels,
            ))
        return results

    def _infer_relationships(self, col: str, df: pd.DataFrame) -> list[dict[str, str]]:
        rels: list[dict[str, str]] = []
        term_name = _match_term(col)
        if term_name and term_name in self.terms:
            term = self.terms[term_name]
            if term.parent:
                rels.append({"type": "part_of", "target": term.parent})
            for child in term.children:
                # Only report child relationship if a matching column exists in the data
                child_term = self.terms.get(child)
                all_names = [child] + (child_term.synonyms if child_term else [])
                if any(c in df.columns for c in all_names):
                    rels.append({"type": "has_child", "target": child})
        return rels

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "domain": "sales",
            "terms": {name: term.to_dict() for name, term in self.terms.items()},
        }
