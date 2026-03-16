"""Conversational prompt engine for querying dashboard report data."""

import json
import re
from typing import Any


def answer_question(question: str, report: dict) -> str:
    """Answer a natural language question using the loaded report data."""
    q = question.lower().strip()
    data_type = report.get("data_type", "")
    summary = report.get("summary", {})
    is_sc = data_type == "supply_chain"

    # Greeting / help
    if _matches(q, ["hello", "hi", "hey", "help", "what can you do", "what can i ask"]):
        return _help_text(is_sc)

    # Summary / overview
    if _matches(q, ["summary", "overview", "how are we doing", "overall", "high level", "tell me about"]):
        return _format_summary(summary, is_sc)

    # OTIF questions (supply chain)
    if _matches(q, ["otif", "on time in full", "on-time"]):
        return _otif_answer(q, report)

    # Fill rate questions
    if _matches(q, ["fill rate", "fill %"]):
        return _fill_answer(q, report)

    # Revenue questions
    if _matches(q, ["revenue", "sales total", "total sales", "how much did we sell"]):
        return _revenue_answer(q, report)

    # Top products / best performers
    if _matches(q, ["top product", "best product", "best seller", "top seller", "highest revenue"]):
        return _top_products_answer(report)

    # Corp / company performance
    if _matches(q, ["corp", "company", "customer", "distributor", "walmart", "costco", "kroger"]):
        return _corp_answer(q, report)

    # Plan / AOP / attainment
    if _matches(q, ["plan", "aop", "attainment", "target", "variance", "gap", "actual vs"]):
        return _plan_answer(q, report)

    # Trend / month / monthly
    if _matches(q, ["trend", "month", "over time", "trajectory", "improving", "declining"]):
        return _trend_answer(q, report)

    # Correlation
    if _matches(q, ["correlation", "correlat", "relationship", "related"]):
        return _correlation_answer(report)

    # Delivery / not delivered
    if _matches(q, ["deliver", "not delivered", "undelivered", "shipped"]):
        return _delivery_answer(report)

    # Orders / quantity
    if _matches(q, ["order", "quantity", "units", "volume"]):
        return _orders_answer(q, report)

    # Charts
    if _matches(q, ["chart", "graph", "visual", "plot"]):
        return _charts_answer(report)

    # Period / date range
    if _matches(q, ["period", "date range", "when", "timeframe", "time frame"]):
        period = summary.get("period", "unknown")
        return f"The data covers the period: **{period}**."

    # Fallback
    return _fallback(is_sc)


def _matches(q: str, keywords: list[str]) -> bool:
    return any(kw in q for kw in keywords)


def _help_text(is_sc: bool) -> str:
    base = "I can answer questions about your dashboard data. Try asking:\n\n"
    if is_sc:
        return base + (
            "- \"Give me a summary\" — overall KPIs\n"
            "- \"What is our OTIF?\" — on-time in-full performance\n"
            "- \"How is fill rate?\" — fill rate metrics\n"
            "- \"How is Costco doing?\" — corp-level performance\n"
            "- \"Show me the trend\" — monthly trends\n"
            "- \"How are we doing vs plan?\" — plan vs actual attainment\n"
            "- \"Any correlations?\" — relationships between metrics\n"
            "- \"How many orders?\" — order volume\n"
            "- \"What about deliveries?\" — delivery performance\n"
            "- \"What charts are available?\" — list of generated charts"
        )
    return base + (
        "- \"Give me a summary\" — overall KPIs\n"
        "- \"What is total revenue?\" — revenue totals\n"
        "- \"Top products?\" — best selling products\n"
        "- \"Show me the trend\" — monthly trends\n"
        "- \"Any correlations?\" — relationships between metrics\n"
        "- \"What charts are available?\" — list of generated charts"
    )


def _format_summary(summary: dict, is_sc: bool) -> str:
    if is_sc:
        return (
            f"**Overall Summary** ({summary.get('period', 'N/A')})\n\n"
            f"- **Total Orders:** {_fmt_num(summary.get('total_order_qty'))}\n"
            f"- **Total Delivered:** {_fmt_num(summary.get('total_delivered'))}\n"
            f"- **Not Delivered:** {_fmt_num(summary.get('total_not_delivered'))}\n"
            f"- **Avg OTIF:** {summary.get('avg_otif_pct', 'N/A')}%\n"
            f"- **Avg Fill Rate:** {summary.get('avg_fill_pct', 'N/A')}%\n"
            f"- **Overall Fill Rate:** {summary.get('overall_fill_rate_pct', 'N/A')}%\n"
            f"- **Records:** {_fmt_num(summary.get('num_records'))}"
        )
    return (
        f"**Overall Summary** ({summary.get('period', 'N/A')})\n\n"
        f"- **Total Revenue:** ${_fmt_num(summary.get('total_revenue'))}\n"
        f"- **Avg Order Value:** ${_fmt_num(summary.get('avg_order_value'))}\n"
        f"- **Median Order Value:** ${_fmt_num(summary.get('median_order_value'))}\n"
        f"- **Units Sold:** {_fmt_num(summary.get('total_units'))}\n"
        f"- **Transactions:** {_fmt_num(summary.get('num_transactions'))}\n"
        f"- **Revenue Std Dev:** ${_fmt_num(summary.get('revenue_std'))}"
    )


def _otif_answer(q: str, report: dict) -> str:
    summary = report.get("summary", {})
    avg = summary.get("avg_otif_pct", "N/A")
    lines = [f"**Average OTIF: {avg}%**\n"]

    by_corp = report.get("by_corp", [])
    if by_corp:
        lines.append("**By Corp:**")
        for c in by_corp:
            otif_val = c.get("otif", 0)
            pct = f"{otif_val * 100:.1f}%" if isinstance(otif_val, (int, float)) else str(otif_val)
            lines.append(f"- {c.get('corp_name', 'Unknown')}: {pct}")

    return "\n".join(lines)


def _fill_answer(q: str, report: dict) -> str:
    summary = report.get("summary", {})
    avg = summary.get("avg_fill_pct", "N/A")
    overall = summary.get("overall_fill_rate_pct", "N/A")
    lines = [f"**Avg Fill Rate: {avg}%** | **Overall: {overall}%**\n"]

    by_corp = report.get("by_corp", [])
    if by_corp:
        lines.append("**By Corp:**")
        for c in by_corp:
            fill_val = c.get("fill", 0)
            pct = f"{fill_val * 100:.1f}%" if isinstance(fill_val, (int, float)) else str(fill_val)
            lines.append(f"- {c.get('corp_name', 'Unknown')}: {pct}")

    return "\n".join(lines)


def _revenue_answer(q: str, report: dict) -> str:
    summary = report.get("summary", {})
    if report.get("data_type") == "supply_chain":
        return "This is supply chain data — revenue metrics aren't available. Try asking about OTIF, fill rate, or orders."
    return (
        f"**Total Revenue: ${_fmt_num(summary.get('total_revenue'))}**\n\n"
        f"- Avg Order Value: ${_fmt_num(summary.get('avg_order_value'))}\n"
        f"- Median Order Value: ${_fmt_num(summary.get('median_order_value'))}\n"
        f"- Transactions: {_fmt_num(summary.get('num_transactions'))}"
    )


def _top_products_answer(report: dict) -> str:
    products = report.get("top_products", [])
    if not products:
        return "No product-level data available. This may be supply chain data — try asking about corp performance."
    lines = ["**Top Products by Revenue:**\n"]
    for i, p in enumerate(products[:10], 1):
        lines.append(f"{i}. **{p.get('product', 'N/A')}** — ${_fmt_num(p.get('total_revenue'))} ({_fmt_num(p.get('num_orders'))} orders)")
    return "\n".join(lines)


def _corp_answer(q: str, report: dict) -> str:
    by_corp = report.get("by_corp", [])
    if not by_corp:
        return "No corp-level data available in this report."

    # Check if asking about a specific corp
    for c in by_corp:
        name = c.get("corp_name", "").lower()
        if name and name in q:
            otif = c.get("otif", 0)
            fill = c.get("fill", 0)
            otif_pct = f"{otif * 100:.1f}%" if isinstance(otif, (int, float)) else str(otif)
            fill_pct = f"{fill * 100:.1f}%" if isinstance(fill, (int, float)) else str(fill)
            return (
                f"**{c.get('corp_name')}**\n\n"
                f"- Orders: {_fmt_num(c.get('order_qty'))}\n"
                f"- Delivered: {_fmt_num(c.get('total_delivered_qty'))}\n"
                f"- OTIF: {otif_pct}\n"
                f"- Fill Rate: {fill_pct}"
            )

    # General corp overview
    lines = ["**Performance by Corp:**\n"]
    for c in by_corp:
        otif = c.get("otif", 0)
        otif_pct = f"{otif * 100:.1f}%" if isinstance(otif, (int, float)) else str(otif)
        lines.append(f"- **{c.get('corp_name', 'N/A')}**: {_fmt_num(c.get('order_qty'))} orders, OTIF {otif_pct}")
    return "\n".join(lines)


def _plan_answer(q: str, report: dict) -> str:
    plan = report.get("plan_comparison")
    if not plan or not plan.get("summary"):
        return "No plan/AOP data has been uploaded yet. Use the **Upload Plan** button to add your AOP file for plan vs actual comparison."

    ps = plan["summary"]
    lines = [
        "**Plan vs Actual Summary**\n",
        f"- **Plan Units:** {_fmt_num(ps.get('total_plan_units'))}",
        f"- **Actual Orders:** {_fmt_num(ps.get('total_actual_orders'))}",
        f"- **Actual Delivered:** {_fmt_num(ps.get('total_actual_delivered'))}",
        f"- **Order Attainment:** {ps.get('order_attainment_pct', 'N/A')}%",
        f"- **Delivery Attainment:** {ps.get('delivery_attainment_pct', 'N/A')}%",
        f"- **Order Gap:** {_fmt_num(ps.get('order_gap'))}",
        f"- **Months Compared:** {ps.get('months_compared', 'N/A')}",
    ]

    # Worst performing month
    by_month = plan.get("by_month", [])
    if by_month:
        worst = min(by_month, key=lambda m: m.get("order_attainment_pct", 100))
        lines.append(f"\n**Lowest attainment month:** {worst.get('month_str', 'N/A')} at {worst.get('order_attainment_pct', 'N/A')}%")

    # By corp if asking
    if _matches(q, ["by corp", "by company", "by customer", "corp breakdown"]):
        by_corp = plan.get("by_corp", [])
        if by_corp:
            lines.append("\n**By Corp:**")
            for c in by_corp:
                lines.append(f"- {c.get('corp', 'N/A')}: {c.get('order_attainment_pct', 'N/A')}% attainment ({_fmt_num(c.get('actual_orders'))} / {_fmt_num(c.get('plan_units'))})")

    return "\n".join(lines)


def _trend_answer(q: str, report: dict) -> str:
    trend = report.get("monthly_trend", [])
    if not trend:
        return "No monthly trend data available."

    is_sc = report.get("data_type") == "supply_chain"
    lines = ["**Monthly Trend:**\n"]

    for t in trend:
        date = t.get("date", "N/A")
        if is_sc:
            otif = t.get("otif", 0)
            otif_pct = f"{otif * 100:.1f}%" if isinstance(otif, (int, float)) else str(otif)
            lines.append(f"- **{date}**: {_fmt_num(t.get('order_qty'))} orders, OTIF {otif_pct}")
        else:
            lines.append(f"- **{date}**: ${_fmt_num(t.get('total_revenue'))} revenue, {_fmt_num(t.get('num_orders'))} orders")

    # Direction
    if len(trend) >= 2:
        if is_sc:
            first = trend[0].get("otif", 0) or 0
            last = trend[-1].get("otif", 0) or 0
            direction = "improving" if last > first else "declining" if last < first else "stable"
            lines.append(f"\nOTIF is **{direction}** over the period.")
        else:
            first = trend[0].get("total_revenue", 0) or 0
            last = trend[-1].get("total_revenue", 0) or 0
            direction = "growing" if last > first else "declining" if last < first else "stable"
            lines.append(f"\nRevenue is **{direction}** over the period.")

    return "\n".join(lines)


def _correlation_answer(report: dict) -> str:
    corr = report.get("correlation")
    if not corr:
        return "No correlation analysis available in this report."

    strong = corr.get("strong_correlations", [])
    if not strong:
        return "No strong correlations found (|r| < 0.5) among the numeric columns."

    lines = ["**Strong Correlations Found:**\n"]
    for c in strong:
        sign = "+" if c["correlation"] > 0 else ""
        lines.append(f"- **{c['col_1']}** ↔ **{c['col_2']}**: {sign}{c['correlation']:.4f} ({c['strength']})")
    return "\n".join(lines)


def _delivery_answer(report: dict) -> str:
    summary = report.get("summary", {})
    if report.get("data_type") != "supply_chain":
        return "This is revenue data — delivery metrics aren't available."
    return (
        f"**Delivery Performance:**\n\n"
        f"- Total Delivered: {_fmt_num(summary.get('total_delivered'))}\n"
        f"- Not Delivered: {_fmt_num(summary.get('total_not_delivered'))}\n"
        f"- Overall Fill Rate: {summary.get('overall_fill_rate_pct', 'N/A')}%\n"
        f"- Avg Fill Rate: {summary.get('avg_fill_pct', 'N/A')}%"
    )


def _orders_answer(q: str, report: dict) -> str:
    summary = report.get("summary", {})
    if report.get("data_type") == "supply_chain":
        return (
            f"**Order Volume:**\n\n"
            f"- Total Orders: {_fmt_num(summary.get('total_order_qty'))}\n"
            f"- Total Delivered: {_fmt_num(summary.get('total_delivered'))}\n"
            f"- Records: {_fmt_num(summary.get('num_records'))}"
        )
    return (
        f"**Order Volume:**\n\n"
        f"- Units Sold: {_fmt_num(summary.get('total_units'))}\n"
        f"- Transactions: {_fmt_num(summary.get('num_transactions'))}\n"
        f"- Avg Order Value: ${_fmt_num(summary.get('avg_order_value'))}"
    )


def _charts_answer(report: dict) -> str:
    charts = report.get("charts", [])
    if not charts:
        return "No charts have been generated yet. Upload data to generate charts."
    lines = ["**Available Charts:**\n"]
    for c in charts:
        name = c.split("/")[-1].replace(".png", "").replace("_", " ").title()
        lines.append(f"- {name}")
    return "\n".join(lines)


def _fallback(is_sc: bool) -> str:
    return (
        "I'm not sure how to answer that. Try one of these:\n\n"
        + ("- \"summary\" — overall metrics\n"
           "- \"otif\" — on-time in-full\n"
           "- \"fill rate\" — fill performance\n"
           "- \"corp performance\" — by company\n"
           "- \"trend\" — monthly trends\n"
           "- \"plan attainment\" — plan vs actual\n"
           "- \"help\" — full list of questions"
           if is_sc else
           "- \"summary\" — overall metrics\n"
           "- \"revenue\" — revenue details\n"
           "- \"top products\" — best sellers\n"
           "- \"trend\" — monthly trends\n"
           "- \"help\" — full list of questions")
    )


def _fmt_num(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        num = float(val)
        if num == int(num):
            return f"{int(num):,}"
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(val)
