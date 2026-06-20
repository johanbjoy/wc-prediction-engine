import plotly.graph_objects as go
import streamlit as st

def render_probability_donut(row):
    """Render a Probability Donut with Confidence Cone from the spec"""
    labels = ['Home Win', 'Draw', 'Away Win']
    values = [row['home_win_prob'], row['draw_prob'], row['away_win_prob']]
    colors = ['#06b6d4', '#8b5cf6', '#10b981'] # Cyan, Violet, Green

    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=.6,
        marker_colors=colors,
        textinfo='label+percent',
        hoverinfo='label+percent',
        textposition='outside'
    )])

    # Command Center styling
    fig.update_layout(
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=20, l=20, r=20),
        font=dict(color='#f9fafb', family='Inter'),
        annotations=[dict(text='Win<br>Probs', x=0.5, y=0.5, font_size=20, showarrow=False, font_color='#9ca3af')]
    )

    return fig

def render_uncertainty_timeline():
    """Render Uncertainty Timeline (in-play placeholder)"""
    fig = go.Figure()
    
    # Placeholder data
    minutes = list(range(0, 91, 5))
    epistemic = [10, 9, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2, 1, 1, 0]
    aleatoric = [15, 15, 14, 13, 12, 11, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 0]
    
    fig.add_trace(go.Scatter(
        x=minutes, y=epistemic, mode='lines', 
        name='Epistemic (Model) Uncertainty',
        line=dict(color='#8b5cf6', width=2),
        fill='tozeroy',
        fillcolor='rgba(139, 92, 246, 0.2)'
    ))
    
    fig.add_trace(go.Scatter(
        x=minutes, y=aleatoric, mode='lines', 
        name='Aleatoric (Match) Uncertainty',
        line=dict(color='#06b6d4', width=2),
        fill='tonexty',
        fillcolor='rgba(6, 182, 212, 0.2)'
    ))

    fig.update_layout(
        title="In-Play Uncertainty Resolution",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f9fafb', family='Inter'),
        xaxis=dict(title='Match Minute', showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='Uncertainty %', showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig
