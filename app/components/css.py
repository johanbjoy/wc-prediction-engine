import streamlit as st

def apply_command_center_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

    :root {
        --bg-primary: #0a0e1a;
        --bg-surface: #111827;
        --bg-elevated: #1f2937;
        --text-primary: #f9fafb;
        --text-secondary: #9ca3af;
        
        --accent-cyan: #06b6d4;
        --accent-violet: #8b5cf6;
        --accent-amber: #f59e0b;
        --accent-green: #10b981;
        --accent-red: #ef4444;
        
        --font-display: 'Orbitron', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
        --font-body: 'Inter', sans-serif;
    }

    .stApp {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        font-family: var(--font-body);
        background-image: radial-gradient(circle at top right, rgba(6, 182, 212, 0.1), transparent 50%),
                          radial-gradient(circle at bottom left, rgba(139, 92, 246, 0.1), transparent 50%);
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-display) !important;
        letter-spacing: 1px;
    }

    .header-text {
        font-family: var(--font-display);
        font-weight: 900;
        font-size: 4rem !important;
        text-transform: uppercase;
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-violet));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-top: 10px;
        margin-bottom: 5px;
        text-shadow: 0 0 20px rgba(6, 182, 212, 0.3);
    }

    .subheader-text {
        font-family: var(--font-mono);
        color: var(--text-secondary);
        font-size: 1rem;
        text-align: center;
        margin-bottom: 40px;
        text-transform: uppercase;
        letter-spacing: 3px;
    }

    /* Cards */
    [data-testid="stMetric"] {
        background-color: var(--bg-surface);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        transition: all 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: var(--accent-cyan);
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(6, 182, 212, 0.15);
    }
    
    .score-card {
        background: var(--bg-elevated);
        border-radius: 12px;
        padding: 15px 20px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 4px solid var(--accent-violet);
        transition: all 0.2s ease;
    }
    .score-card:hover {
        border-color: var(--accent-cyan);
        background: rgba(31, 41, 55, 0.8);
    }
    .score-team {
        font-size: 1.2rem;
        font-weight: 600;
        flex: 1;
    }
    .score-home { text-align: right; }
    .score-away { text-align: left; }
    .score-center {
        flex: 0.6;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .score-actual {
        font-family: var(--font-display);
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: 2px;
        margin: 5px 0;
    }
    
    /* Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-family: var(--font-mono);
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 1px;
    }
    .badge-exact {
        background: rgba(16, 185, 129, 0.2);
        color: var(--accent-green);
        border: 1px solid var(--accent-green);
    }
    .badge-correct {
        background: rgba(6, 182, 212, 0.2);
        color: var(--accent-cyan);
        border: 1px solid var(--accent-cyan);
    }
    .badge-wrong {
        background: rgba(239, 68, 68, 0.2);
        color: var(--accent-red);
        border: 1px solid var(--accent-red);
    }
    
    /* Overrides */
    div[data-testid="stMetricValue"] {
        font-family: var(--font-display);
        color: var(--text-primary);
    }
    
    /* Hide the redundant 'main.py' entry from the sidebar */
    [data-testid="stSidebarNav"] ul li:first-child {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
