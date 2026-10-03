from __future__ import annotations

import plotly.graph_objects as go


def metric_bars(metrics: dict) -> go.Figure:
    labels = ["Execution ms", "Planning ms", "Rows", "Shared hits", "Shared reads"]
    values = [
        metrics.get("execution_time_ms") or 0,
        metrics.get("planning_time_ms") or 0,
        metrics.get("rows") or 0,
        metrics.get("shared_hit_blocks") or 0,
        metrics.get("shared_read_blocks") or 0,
    ]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color="#3b82f6"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.3)",
        font_color="#e2e8f0",
        margin=dict(l=20, r=20, t=30, b=20),
        height=280,
        title="Measured query metrics",
    )
    return fig


def before_after(baseline: dict | None, optimized: dict | None) -> go.Figure:
    fig = go.Figure()
    if baseline:
        fig.add_trace(
            go.Bar(
                name="Before (measured)",
                x=["Execution ms", "Planning ms", "Shared reads"],
                y=[
                    baseline.get("execution_time_ms") or 0,
                    baseline.get("planning_time_ms") or 0,
                    baseline.get("shared_read_blocks") or 0,
                ],
                marker_color="#f97316",
            )
        )
    if optimized:
        fig.add_trace(
            go.Bar(
                name="After (measured)",
                x=["Execution ms", "Planning ms", "Shared reads"],
                y=[
                    optimized.get("execution_time_ms") or 0,
                    optimized.get("planning_time_ms") or 0,
                    optimized.get("shared_read_blocks") or 0,
                ],
                marker_color="#22c55e",
            )
        )
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.3)",
        font_color="#e2e8f0",
        margin=dict(l=20, r=20, t=30, b=20),
        height=320,
        title="Sandbox before / after",
    )
    return fig


def plan_graph_figure(nodes: list[dict], edges: list[dict]) -> go.Figure:
    if not nodes:
        fig = go.Figure()
        fig.update_layout(title="No plan graph yet", height=320, paper_bgcolor="rgba(0,0,0,0)")
        return fig
    n = len(nodes)
    xs, ys = [], []
    for node in nodes:
        depth = node.get("depth", 0)
        xs.append(node.get("id", 0))
        ys.append(-depth if depth else -node.get("id", 0) % max(n, 1))
    # simple layered layout from ids
    by_depth: dict[int, list[int]] = {}
    for i, node in enumerate(nodes):
        d = int(node.get("id", i))
        by_depth.setdefault(d, []).append(i)
    positions = {}
    for i, node in enumerate(nodes):
        positions[i] = (i, -i)
    if edges:
        from collections import defaultdict

        children = defaultdict(list)
        incoming = set()
        for edge in edges:
            children[edge["source"]].append(edge["target"])
            incoming.add(edge["target"])
        # actually edges are child -> parent in our builder
        parent_of = {}
        kids = defaultdict(list)
        for edge in edges:
            kids[edge["target"]].append(edge["source"])
            parent_of[edge["source"]] = edge["target"]
        roots = [i for i in range(n) if i not in parent_of]
        levels: dict[int, int] = {r: 0 for r in roots}

        def walk(i: int, depth: int) -> None:
            for child in kids.get(i, []):
                levels[child] = depth + 1
                walk(child, depth + 1)

        for r in roots:
            walk(r, 0)
        layer_count: dict[int, int] = defaultdict(int)
        positions = {}
        for i in range(n):
            d = levels.get(i, 0)
            positions[i] = (layer_count[d], -d)
            layer_count[d] += 1

    edge_x, edge_y = [], []
    for edge in edges:
        x0, y0 = positions[edge["source"]]
        x1, y1 = positions[edge["target"]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    node_x = [positions[i][0] for i in range(n)]
    node_y = [positions[i][1] for i in range(n)]
    importance = [node.get("importance") or 0 for node in nodes]
    labels = [
        f"{node.get('node_type')}<br>{node.get('relation') or ''}<br>rows={node.get('actual_rows')}"
        for node in nodes
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color="#64748b", width=1), hoverinfo="none"))
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=[node.get("node_type") for node in nodes],
            textposition="top center",
            marker=dict(
                size=[18 + 24 * (imp or 0) for imp in importance],
                color=importance,
                colorscale="YlOrRd",
                showscale=True,
                colorbar=dict(title="Importance"),
            ),
            hovertext=labels,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.3)",
        font_color="#e2e8f0",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=380,
        margin=dict(l=20, r=20, t=30, b=20),
        title="Execution plan graph (expensive nodes highlighted)",
    )
    return fig
