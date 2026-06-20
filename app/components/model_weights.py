import plotly.graph_objects as go
import streamlit as st

def render_model_attribution():
    """Render Model Attribution Waterfall (SHAP-style) from the spec"""
    fig = go.Figure(go.Waterfall(
        name="2026 Model Weights", orientation="v",
        measure=["relative", "relative", "relative", "relative", "relative", "total"],
        x=["Base xG", "LightGBM", "TabNet", "Temporal Fusion", "Causal Engine", "Final Deep Stack"],
        textposition="outside",
        text=["1.0", "+0.4", "+0.2", "-0.1", "+0.3", "1.8 xG"],
        y=[1.0, 0.4, 0.2, -0.1, 0.3, 1.8],
        connector={"line":{"color":"#374151"}},
        decreasing={"marker":{"color":"#ef4444"}},
        increasing={"marker":{"color":"#10b981"}},
        totals={"marker":{"color":"#06b6d4"}}
    ))

    fig.update_layout(
        title="Model Attribution Waterfall (xG Impact)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f9fafb', family='Inter'),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
    )
    return fig

def render_dynamic_routing(weights=[0.45, 0.35, 0.20]):
    """Render the dynamic routing neural network weights"""
    models = ['LightGBM (ML)', 'TabNet (Deep Learning)', 'Temporal Fusion (Time-Series)']
    colors = ['#06b6d4', '#8b5cf6', '#f59e0b']
    
    fig = go.Figure(go.Bar(
        x=weights,
        y=models,
        orientation='h',
        marker=dict(color=colors, line=dict(width=1, color='rgba(255,255,255,0.2)')),
        text=[f"{w*100:.0f}%" for w in weights],
        textposition='inside'
    ))
    
    fig.update_layout(
        title="Dynamic Router Allocation",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f9fafb', family='Inter'),
        xaxis=dict(showgrid=False, range=[0, 1]),
        yaxis=dict(showgrid=False)
    )
    return fig
