import plotly.graph_objects as go

def render_calibration_reliability():
    """Render Calibration Reliability Diagram from the spec"""
    fig = go.Figure()
    
    # Perfect calibration line
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], 
        mode='lines', name='Perfect Calibration',
        line=dict(color='#9ca3af', dash='dash')
    ))
    
    # V2 Venn-ABERS Calibrated
    fig.add_trace(go.Scatter(
        x=[0.1, 0.3, 0.5, 0.7, 0.9], 
        y=[0.09, 0.31, 0.49, 0.72, 0.89], 
        mode='lines+markers', name='V2 Deep Stack (Venn-ABERS)',
        line=dict(color='#10b981', width=3),
        marker=dict(size=8)
    ))

    # V1 CatBoost Raw
    fig.add_trace(go.Scatter(
        x=[0.1, 0.3, 0.5, 0.7, 0.9], 
        y=[0.15, 0.25, 0.40, 0.80, 0.95], 
        mode='lines+markers', name='V1 Baseline (Uncalibrated)',
        line=dict(color='#ef4444', width=2, dash='dot'),
        marker=dict(size=6)
    ))

    fig.update_layout(
        title="Bayesian Calibration Reliability",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f9fafb', family='Inter'),
        xaxis=dict(title='Predicted Probability', range=[0, 1], showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='Empirical Frequency', range=[0, 1], showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig
