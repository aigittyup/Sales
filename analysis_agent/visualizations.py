"""Sales data visualization generators."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd


def setup_style():
    """Configure consistent plot styling."""
    sns.set_theme(style="whitegrid", palette="husl")
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
    """Generate a pie chart for segment revenue distribution."""
    setup_style()
    fig, ax = plt.subplots()

    ax.pie(
        segment_df["total_revenue"],
        labels=segment_df[segment_col],
        autopct="%1.1f%%",
        startangle=140,
    )
    ax.set_title(f"Revenue by {segment_col.replace('_', ' ').title()}")
    plt.tight_layout()

    filepath = str(Path(output_path) / f"segment_{segment_col}.png")
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
