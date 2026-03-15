"""Sales and supply chain data visualization generators."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd

# Interstate Batteries brand colors
IB_GREEN = "#00843D"
IB_GREEN_DARK = "#005a28"
IB_GREEN_LIGHT = "#4CAF50"
IB_PALETTE = [IB_GREEN, "#2196F3", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4", "#FF5722", "#795548"]


def setup_style():
    """Configure consistent plot styling."""
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "figure.figsize": (12, 6),
        "figure.dpi": 150,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
    })


def plot_revenue_trend(monthly_trend: pd.DataFrame, output_path: str, date_col: str = "date") -> str:
    """Generate a monthly revenue trend line chart."""
    setup_style()
    fig, ax = plt.subplots()

    ax.plot(monthly_trend[date_col], monthly_trend["total_revenue"], marker="o", linewidth=2)
    ax.fill_between(monthly_trend[date_col], monthly_trend["total_revenue"], alpha=0.15)
    ax.set_title("Monthly Revenue Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue ($)")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    fig.autofmt_xdate()
    plt.tight_layout()

    filepath = str(Path(output_path) / "revenue_trend.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


def plot_top_products(top_products: pd.DataFrame, output_path: str, product_col: str = "product") -> str:
    """Generate a horizontal bar chart of top products by revenue."""
    setup_style()
    fig, ax = plt.subplots()

    data = top_products.sort_values("total_revenue", ascending=True)
    ax.barh(data[product_col], data["total_revenue"], color=sns.color_palette("husl", len(data)))
    ax.set_title("Top Products by Revenue")
    ax.set_xlabel("Revenue ($)")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    plt.tight_layout()

    filepath = str(Path(output_path) / "top_products.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


def plot_segment_breakdown(segment_df: pd.DataFrame, segment_col: str, output_path: str) -> str:
    """Generate a grouped bar chart for segment revenue distribution."""
    setup_style()
    fig, ax = plt.subplots()

    data = segment_df.sort_values("total_revenue", ascending=True)
    bars = ax.barh(data[segment_col], data["total_revenue"], color=sns.color_palette("husl", len(data)))

    # Add percentage labels on bars
    total = data["total_revenue"].sum()
    for bar, val in zip(bars, data["total_revenue"]):
        pct = val / total * 100
        ax.text(bar.get_width() + total * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%", va="center", fontsize=10)

    ax.set_title(f"Revenue by {segment_col.replace('_', ' ').title()}")
    ax.set_xlabel("Revenue ($)")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    plt.tight_layout()

    filepath = str(Path(output_path) / f"segment_{segment_col}.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


def plot_correlation_heatmap(corr_matrix: pd.DataFrame, output_path: str) -> str:
    """Generate a correlation heatmap for numeric columns."""
    setup_style()
    fig, ax = plt.subplots(figsize=(10, 8))

    mask = None
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Correlation Matrix (Numeric Columns)")
    plt.tight_layout()

    filepath = str(Path(output_path) / "correlation_heatmap.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


def plot_growth_rates(growth_df: pd.DataFrame, output_path: str, date_col: str = "date") -> str:
    """Generate a bar chart of month-over-month growth rates."""
    setup_style()
    fig, ax = plt.subplots()

    data = growth_df.dropna(subset=["mom_growth_pct"])
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in data["mom_growth_pct"]]
    ax.bar(data[date_col].dt.strftime("%Y-%m"), data["mom_growth_pct"], color=colors)
    ax.set_title("Month-over-Month Revenue Growth (%)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Growth (%)")
    ax.axhline(y=0, color="black", linewidth=0.5)
    fig.autofmt_xdate()
    plt.tight_layout()

    filepath = str(Path(output_path) / "growth_rates.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


# --- Supply chain visualizations ---

def plot_otif_fill_trend(monthly_trend: pd.DataFrame, output_path: str, date_col: str = "date") -> str:
    """Generate OTIF % and Fill % trend over time."""
    setup_style()
    fig, ax = plt.subplots()

    otif_col = next((c for c in monthly_trend.columns if "otif" in c), None)
    fill_col = next((c for c in monthly_trend.columns if "fill" in c), None)

    if otif_col:
        ax.plot(monthly_trend[date_col], monthly_trend[otif_col] * 100, marker="o",
                linewidth=2, color=IB_GREEN, label="OTIF %")
    if fill_col:
        ax.plot(monthly_trend[date_col], monthly_trend[fill_col] * 100, marker="s",
                linewidth=2, color="#2196F3", label="Fill %")

    ax.set_title("OTIF % and Fill % Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Percentage (%)")
    ax.set_ylim(0, 105)
    ax.axhline(y=95, color="#E91E63", linestyle="--", linewidth=1, alpha=0.6, label="95% Target")
    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()

    filepath = str(Path(output_path) / "otif_fill_trend.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


def plot_order_volume_trend(monthly_trend: pd.DataFrame, output_path: str, date_col: str = "date") -> str:
    """Generate order quantity and delivered quantity trend."""
    setup_style()
    fig, ax = plt.subplots()

    qty_col = next((c for c in monthly_trend.columns if "order_qty" in c), None)
    del_col = next((c for c in monthly_trend.columns if "total_delivered" in c), None)

    if qty_col:
        ax.bar(monthly_trend[date_col], monthly_trend[qty_col], width=20,
               color=IB_GREEN, alpha=0.7, label="Order Qty")
    if del_col:
        ax.bar(monthly_trend[date_col], monthly_trend[del_col], width=20,
               color="#2196F3", alpha=0.5, label="Delivered Qty")

    ax.set_title("Monthly Order Volume")
    ax.set_xlabel("Month")
    ax.set_ylabel("Quantity")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()

    filepath = str(Path(output_path) / "order_volume_trend.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


def plot_corp_performance(by_corp: pd.DataFrame, output_path: str) -> str:
    """Generate horizontal bar chart of corporate performance."""
    setup_style()
    corp_col = by_corp.columns[0]
    otif_col = next((c for c in by_corp.columns if "otif" in c), None)
    qty_col = next((c for c in by_corp.columns if "order_qty" in c), None)

    fig, axes = plt.subplots(1, 2, figsize=(14, max(6, len(by_corp) * 0.5)))

    if qty_col:
        data = by_corp.sort_values(qty_col, ascending=True)
        axes[0].barh(data[corp_col], data[qty_col], color=IB_GREEN)
        axes[0].set_title("Order Qty by Corp")
        axes[0].xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    if otif_col:
        data = by_corp.sort_values(otif_col, ascending=True)
        colors = [IB_GREEN if v >= 0.95 else "#FF9800" if v >= 0.90 else "#E91E63" for v in data[otif_col]]
        axes[1].barh(data[corp_col], data[otif_col] * 100, color=colors)
        axes[1].set_title("Avg OTIF % by Corp")
        axes[1].set_xlabel("OTIF %")
        axes[1].axvline(x=95, color="#E91E63", linestyle="--", linewidth=1, alpha=0.6)

    plt.tight_layout()
    filepath = str(Path(output_path) / "corp_performance.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath


def plot_group_performance(by_group: pd.DataFrame, output_path: str) -> str:
    """Generate bar chart of performance by group size."""
    setup_style()
    group_col = by_group.columns[0]
    qty_col = next((c for c in by_group.columns if "order_qty" in c), None)
    otif_col = next((c for c in by_group.columns if "otif" in c), None)

    fig, ax = plt.subplots()

    if qty_col:
        data = by_group.sort_values(qty_col, ascending=False)
        bars = ax.bar(data[group_col].astype(str), data[qty_col], color=IB_GREEN, alpha=0.8)

        # Add OTIF % labels on bars
        if otif_col:
            for bar, otif_val in zip(bars, data[otif_col]):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        f"{otif_val * 100:.1f}%", ha="center", va="bottom", fontsize=9,
                        color=IB_GREEN_DARK, fontweight="bold")

    ax.set_title("Order Volume by Group Size (with OTIF %)")
    ax.set_xlabel("Group Size")
    ax.set_ylabel("Order Qty")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    plt.tight_layout()

    filepath = str(Path(output_path) / "group_performance.png")
    fig.savefig(filepath)
    plt.close(fig)
    return filepath
