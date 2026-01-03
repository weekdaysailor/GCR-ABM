import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from gcr_model import GCR_ABM_Simulation

# Page configuration
st.set_page_config(
    page_title="GCR ABM Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<p class="main-header">🌍 Global Carbon Reward (GCR) ABM Dashboard</p>', unsafe_allow_html=True)
st.markdown("**Agent-Based Model** simulating carbon sequestration economy with XCR tokens and CQE")

# Sidebar - Simulation Parameters
st.sidebar.header("Simulation Parameters")

years = st.sidebar.slider("Simulation Years", min_value=10, max_value=100, value=50, step=10)
price_floor = st.sidebar.slider("XCR Price Floor (Initial, USD)", min_value=0, max_value=999, value=100, step=10)
adoption_rate = st.sidebar.slider("GCR Adoption Rate (countries/year)", min_value=0.0, max_value=10.0, value=3.5, step=0.5)
enable_audits = st.sidebar.checkbox("Enable Audits", value=True)
random_seed = st.sidebar.number_input("Random Seed (0 = random)", min_value=0, max_value=10000, value=42)

run_button = st.sidebar.button("Run Simulation", type="primary", width='stretch')

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
    st.session_state.sim = None

# Run simulation
if run_button:
    with st.spinner("Running simulation..."):
        if random_seed > 0:
            np.random.seed(random_seed)

        sim = GCR_ABM_Simulation(years=years, enable_audits=enable_audits, price_floor=price_floor, adoption_rate=adoption_rate)
        df = sim.run_simulation()

        st.session_state.df = df
        st.session_state.sim = sim
        st.success(f"Simulation complete! {years} years simulated.")

# Display results if available
if st.session_state.df is not None:
    df = st.session_state.df
    sim = st.session_state.sim

    # Summary Metrics
    st.header("📊 Summary Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        co2_reduction = 420.0 - df.iloc[-1]['CO2_ppm']
        st.metric(
            "CO2 Reduction",
            f"{co2_reduction:.2f} ppm",
            delta=f"-{(co2_reduction/420.0)*100:.1f}%"
        )

    with col2:
        co2_avoided = df.iloc[-1]['CO2_Avoided']
        st.metric(
            "CO2 Avoided vs BAU",
            f"{co2_avoided:.2f} ppm",
            delta="GCR Impact"
        )

    with col3:
        st.metric(
            "Final XCR Supply",
            f"{df.iloc[-1]['XCR_Supply']:.2e}",
            delta=f"{df.iloc[-1]['XCR_Minted']:.2e} last year"
        )

    with col4:
        st.metric(
            "Active Countries",
            f"{int(df.iloc[-1]['Active_Countries'])}",
            delta=f"Started with {int(df.iloc[0]['Active_Countries'])}"
        )

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric(
            "Operational Projects",
            f"{int(df.iloc[-1]['Projects_Operational'])}",
            delta=f"{int(df.iloc[-1]['Projects_Total'])} total"
        )

    with col6:
        st.metric(
            "Market Price",
            f"${df.iloc[-1]['Market_Price']:.2f}",
            delta=f"Floor: ${df.iloc[-1]['Price_Floor']:.0f}"
        )

    with col7:
        st.metric(
            "Final Inflation",
            f"{df.iloc[-1]['Inflation']*100:.2f}%",
            delta=f"{(df.iloc[-1]['Inflation']-0.02)*100:.2f}pp",
            delta_color="inverse"
        )

    with col8:
        st.metric(
            "CQE Budget",
            f"${df.iloc[-1]['CQE_Budget_Total']/1e12:.2f}T",
            delta=f"Started ${df.iloc[0]['CQE_Budget_Total']/1e12:.2f}T"
        )

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🌡️ Climate & CO2",
        "💰 XCR Economics",
        "📈 Market Dynamics",
        "🏗️ Projects",
        "📋 Data Table"
    ])

    # Tab 1: Climate & CO2
    with tab1:
        st.subheader("Atmospheric CO2 & Sequestration")

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Atmospheric CO2 Concentration (GCR vs BAU)", "Annual Sequestration"),
            vertical_spacing=0.15,
            specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
        )

        # BAU CO2 levels (Business As Usual - no intervention)
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['BAU_CO2_ppm'],
                name="BAU (No GCR)",
                line=dict(color='#7f7f7f', width=2, dash='dot'),
                fill='tozeroy',
                fillcolor='rgba(127, 127, 127, 0.1)'
            ),
            row=1, col=1
        )

        # GCR CO2 levels
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['CO2_ppm'],
                name="With GCR",
                line=dict(color='#2ca02c', width=3),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)'
            ),
            row=1, col=1
        )

        # Target line
        fig.add_hline(
            y=350.0,
            line_dash="dash",
            line_color="blue",
            annotation_text="Target (350 ppm)",
            row=1, col=1
        )

        # Sequestration
        fig.add_trace(
            go.Bar(
                x=df['Year'],
                y=df['Sequestration_Tonnes'],
                name="Sequestration (tonnes/year)",
                marker_color='#2ca02c',
                opacity=0.7
            ),
            row=2, col=1
        )

        # Projects operational (secondary axis)
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Projects_Operational'],
                name="Operational Projects",
                line=dict(color='#ff7f0e', width=2, dash='dot'),
                yaxis='y3'
            ),
            row=2, col=1,
            secondary_y=True
        )

        fig.update_xaxes(title_text="Year", row=2, col=1)
        fig.update_yaxes(title_text="CO2 (ppm)", row=1, col=1)
        fig.update_yaxes(title_text="Tonnes CO2e/year", row=2, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Project Count", row=2, col=1, secondary_y=True)

        fig.update_layout(height=700, showlegend=True, hovermode='x unified')
        st.plotly_chart(fig, width='stretch')

        # BAU Impact Summary
        st.subheader("GCR Impact vs Business As Usual")
        col1, col2, col3 = st.columns(3)

        with col1:
            final_co2_avoided = df.iloc[-1]['CO2_Avoided']
            st.metric("Final CO2 Avoided", f"{final_co2_avoided:.2f} ppm")

        with col2:
            total_sequestration = df['Sequestration_Tonnes'].sum()
            st.metric("Total Sequestration", f"{total_sequestration:.2e} tonnes")

        with col3:
            bau_growth = ((df.iloc[-1]['BAU_CO2_ppm'] / 420.0) - 1) * 100
            st.metric("BAU CO2 Growth", f"+{bau_growth:.1f}%")

    # Tab 2: XCR Economics
    with tab2:
        st.subheader("XCR Supply, Minting & Burning")

        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                "XCR Total Supply",
                "XCR Minting & Burning (Annual)",
                "Cumulative XCR Burned"
            ),
            vertical_spacing=0.12
        )

        # Total supply
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['XCR_Supply'],
                name="Total XCR Supply",
                line=dict(color='#1f77b4', width=3),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.2)'
            ),
            row=1, col=1
        )

        # Minting (positive) and burning (negative)
        colors = ['green' if x >= 0 else 'red' for x in df['XCR_Minted']]
        fig.add_trace(
            go.Bar(
                x=df['Year'],
                y=df['XCR_Minted'],
                name="XCR Minted (Net)",
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )

        # Cumulative burned
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['XCR_Burned'],
                name="Cumulative XCR Burned",
                line=dict(color='#d62728', width=3),
                fill='tozeroy',
                fillcolor='rgba(214, 39, 40, 0.2)'
            ),
            row=3, col=1
        )

        fig.update_xaxes(title_text="Year", row=3, col=1)
        fig.update_yaxes(title_text="XCR Supply", row=1, col=1)
        fig.update_yaxes(title_text="XCR (Annual)", row=2, col=1)
        fig.update_yaxes(title_text="XCR Burned", row=3, col=1)

        fig.update_layout(height=900, showlegend=True, hovermode='x unified')
        st.plotly_chart(fig, width='stretch')

        # XCR Economics Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            total_minted = df['XCR_Minted'].clip(lower=0).sum()
            st.metric("Total XCR Minted", f"{total_minted:.2e}")
        with col2:
            total_burned = df.iloc[-1]['XCR_Burned']
            st.metric("Total XCR Burned", f"{total_burned:.2e}")
        with col3:
            burn_rate = (total_burned / total_minted * 100) if total_minted > 0 else 0
            st.metric("Burn Rate", f"{burn_rate:.1f}%")

    # Tab 3: Market Dynamics
    with tab3:
        st.subheader("Market Price, Sentiment & Inflation")

        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                "XCR Market Price & Sentiment",
                "Global Inflation Rate",
                "Stability Ratio & CEA Warnings"
            ),
            vertical_spacing=0.12,
            specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": True}]]
        )

        # Price floor (area)
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Price_Floor'],
                name="Price Floor",
                line=dict(color='#1f77b4', width=2, dash='dash'),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.1)'
            ),
            row=1, col=1,
            secondary_y=False
        )

        # Market price
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Market_Price'],
                name="Market Price (USD)",
                line=dict(color='#2ca02c', width=3),
            ),
            row=1, col=1,
            secondary_y=False
        )

        # Sentiment
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Sentiment'],
                name="Investor Sentiment",
                line=dict(color='#ff7f0e', width=2),
            ),
            row=1, col=1,
            secondary_y=True
        )

        # Inflation
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Inflation'] * 100,
                name="Inflation (%)",
                line=dict(color='#d62728', width=3),
                fill='tozeroy',
                fillcolor='rgba(214, 39, 40, 0.1)'
            ),
            row=2, col=1
        )

        # Inflation threshold
        fig.add_hline(
            y=3.0,
            line_dash="dash",
            line_color="orange",
            annotation_text="Brake Threshold (3%)",
            row=2, col=1
        )

        # Calculate Stability Ratio
        cqe_budget = sim.central_bank.total_cqe_budget
        df['Stability_Ratio'] = (df['XCR_Supply'] * df['Market_Price']) / cqe_budget

        # Stability Ratio
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Stability_Ratio'],
                name="Stability Ratio",
                line=dict(color='#9467bd', width=3),
            ),
            row=3, col=1,
            secondary_y=False
        )

        # Warning thresholds
        fig.add_hline(
            y=8.0,
            line_dash="dash",
            line_color="orange",
            annotation_text="8:1 Warning",
            row=3, col=1
        )
        fig.add_hline(
            y=10.0,
            line_dash="dash",
            line_color="red",
            annotation_text="10:1 Brake",
            row=3, col=1
        )

        # Warning count on secondary axis
        df['Warning_Int'] = df['CEA_Warning'].astype(int)
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Warning_Int'],
                name="Warning Status",
                line=dict(color='red', width=1, dash='dot'),
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.1)'
            ),
            row=3, col=1,
            secondary_y=True
        )

        fig.update_xaxes(title_text="Year", row=3, col=1)
        fig.update_yaxes(title_text="Price (USD)", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Sentiment (0-1)", row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="Inflation (%)", row=2, col=1)
        fig.update_yaxes(title_text="Stability Ratio", row=3, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Warning (0/1)", row=3, col=1, secondary_y=True)

        fig.update_layout(height=900, showlegend=True, hovermode='x unified')
        st.plotly_chart(fig, width='stretch')

    # Tab 4: Projects
    with tab4:
        st.subheader("Project Portfolio Analysis")

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Project Status Over Time",
                "Sequestration by Year",
                "Projects by Country",
                "Projects by Channel"
            ),
            specs=[
                [{"type": "scatter"}, {"type": "bar"}],
                [{"type": "pie"}, {"type": "pie"}]
            ],
            vertical_spacing=0.15,
            horizontal_spacing=0.15
        )

        # Project counts over time
        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Projects_Total'],
                name="Total Projects",
                line=dict(color='#1f77b4', width=2),
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Projects_Operational'],
                name="Operational",
                line=dict(color='#2ca02c', width=2),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)'
            ),
            row=1, col=1
        )

        # Sequestration by year (bar chart)
        fig.add_trace(
            go.Bar(
                x=df['Year'],
                y=df['Sequestration_Tonnes'],
                name="Sequestration",
                marker_color='#2ca02c',
                showlegend=False
            ),
            row=1, col=2
        )

        # Projects by country (pie chart)
        country_counts = {}
        for country, data in sim.countries.items():
            country_counts[country] = len(data['projects'])

        fig.add_trace(
            go.Pie(
                labels=list(country_counts.keys()),
                values=list(country_counts.values()),
                name="By Country",
                hole=0.3
            ),
            row=2, col=1
        )

        # Projects by channel (pie chart)
        channel_counts = {
            "CDR": 0,
            "Conventional": 0,
            "Co-benefits": 0
        }
        for project in sim.projects_broker.projects:
            if project.channel.name == "CDR":
                channel_counts["CDR"] += 1
            elif project.channel.name == "CONVENTIONAL":
                channel_counts["Conventional"] += 1
            else:
                channel_counts["Co-benefits"] += 1

        fig.add_trace(
            go.Pie(
                labels=list(channel_counts.keys()),
                values=list(channel_counts.values()),
                name="By Channel",
                hole=0.3
            ),
            row=2, col=2
        )

        fig.update_xaxes(title_text="Year", row=1, col=1)
        fig.update_xaxes(title_text="Year", row=1, col=2)
        fig.update_yaxes(title_text="Project Count", row=1, col=1)
        fig.update_yaxes(title_text="Tonnes CO2e", row=1, col=2)

        fig.update_layout(height=700, showlegend=True)
        st.plotly_chart(fig, width='stretch')

        # Project statistics
        st.subheader("Project Statistics")
        col1, col2, col3, col4 = st.columns(4)

        operational_projects = [p for p in sim.projects_broker.projects if p.status.value == "operational"]
        failed_projects = [p for p in sim.projects_broker.projects if p.status.value == "failed"]

        with col1:
            st.metric("Total Projects Initiated", len(sim.projects_broker.projects))
        with col2:
            st.metric("Currently Operational", len(operational_projects))
        with col3:
            st.metric("Failed Projects", len(failed_projects))
        with col4:
            failure_rate = len(failed_projects) / len(sim.projects_broker.projects) * 100 if len(sim.projects_broker.projects) > 0 else 0
            st.metric("Failure Rate", f"{failure_rate:.1f}%")

        # Country adoption over time
        st.subheader("GCR Country Adoption & CQE Budget Growth")

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Active Countries Over Time", "Total CQE Budget Over Time"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )

        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['Active_Countries'],
                name="Active Countries",
                line=dict(color='#ff7f0e', width=3),
                fill='tozeroy',
                fillcolor='rgba(255, 127, 14, 0.2)'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df['Year'],
                y=df['CQE_Budget_Total'] / 1e12,  # Convert to trillions
                name="CQE Budget",
                line=dict(color='#2ca02c', width=3),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)'
            ),
            row=1, col=2
        )

        fig.update_xaxes(title_text="Year", row=1, col=1)
        fig.update_xaxes(title_text="Year", row=1, col=2)
        fig.update_yaxes(title_text="Number of Countries", row=1, col=1)
        fig.update_yaxes(title_text="USD Trillions", row=1, col=2)

        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width='stretch')

    # Tab 5: Data Table
    with tab5:
        st.subheader("Simulation Data")

        # Display controls
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 Click column headers to sort. Use search box to filter.")
        with col2:
            download_csv = st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode('utf-8'),
                "gcr_simulation_results.csv",
                "text/csv",
                key='download-csv'
            )

        # Format numeric columns for better display
        display_df = df.copy()
        display_df['CO2_ppm'] = display_df['CO2_ppm'].round(2)
        display_df['Inflation'] = (display_df['Inflation'] * 100).round(2)
        display_df['Market_Price'] = display_df['Market_Price'].round(2)
        display_df['Sentiment'] = display_df['Sentiment'].round(3)

        st.dataframe(
            display_df,
            width='stretch',
            height=500
        )

        # Statistical summary
        st.subheader("Statistical Summary")
        st.dataframe(df.describe(), width='stretch')

else:
    # Welcome screen
    st.info("👈 Configure simulation parameters in the sidebar and click 'Run Simulation' to begin.")

    st.markdown("""
    ## About This Dashboard

    This interactive dashboard visualizes the **Global Carbon Reward (GCR) Agent-Based Model**, which simulates:

    - **5 Agent Types**: CEA, Central Bank Alliance, Projects Broker, Investor Market, Auditor
    - **3 Reward Channels**: CDR, Conventional Mitigation, Co-benefits
    - **Carbon Economy**: XCR token minting, burning, and trading
    - **Policy Mechanisms**: R-value economics, CQE floor defense, stability monitoring

    ### Dashboard Features

    - **Climate & CO2**: Track atmospheric CO2 reduction and sequestration rates
    - **XCR Economics**: Monitor token supply, minting, and burning dynamics
    - **Market Dynamics**: Visualize price discovery, sentiment, and inflation
    - **Projects**: Analyze project portfolio by country, channel, and status
    - **Data Table**: Export and explore raw simulation data

    ### Quick Start

    1. Adjust simulation years (10-100) in the sidebar
    2. Enable/disable audits to see impact on XCR burning
    3. Set a random seed for reproducible results
    4. Click "Run Simulation"
    5. Explore results across multiple tabs

    ---

    **Authoritative Source**: This model implements the carbon reward policy described in `docs/chen_chap5.md`
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown("""
**GCR ABM Dashboard**
Agent-Based Model for Global Carbon Rewards

Based on Chen (2025) carbon reward policy framework.
""")
