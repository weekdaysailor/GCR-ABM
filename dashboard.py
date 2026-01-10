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

years = st.sidebar.slider("Simulation Years", min_value=10, max_value=200, value=100, step=10)
price_floor = st.sidebar.slider("XCR Price Floor (Initial, USD)", min_value=0, max_value=999, value=100, step=10)
adoption_rate = st.sidebar.slider("GCR Adoption Rate (countries/year)", min_value=0.0, max_value=10.0, value=3.5, step=0.5)
inflation_target = st.sidebar.slider("Inflation Target (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.25) / 100.0

st.sidebar.markdown("---")
st.sidebar.subheader("BAU Emissions Trajectory")
BASE_YEAR = 2024
bau_peak_calendar_year = st.sidebar.slider(
    "BAU Emissions Peak Year",
    min_value=BASE_YEAR,
    max_value=BASE_YEAR + 20,
    value=BASE_YEAR + 6,  # Default 2030
    step=1,
    help="Calendar year when business-as-usual emissions peak (earlier = faster climate action baseline)"
)
bau_peak_year = bau_peak_calendar_year - BASE_YEAR

st.sidebar.markdown("---")
st.sidebar.subheader("XCR System Ramping")
xcr_start_calendar = st.sidebar.slider("XCR Start Year", min_value=BASE_YEAR, max_value=BASE_YEAR + 20, value=BASE_YEAR + 3, step=1,
                                       help=f"Calendar year when XCR system begins ({BASE_YEAR} = immediate)")
xcr_start_year = xcr_start_calendar - BASE_YEAR
years_to_full_capacity = st.sidebar.slider("Years to Full Capacity", min_value=1, max_value=20, value=5, step=1,
                                           help="Years for system to ramp from 0% to 100% capacity")

st.sidebar.markdown("---")
st.sidebar.subheader("Technology Parameters")
cdr_learning_rate = st.sidebar.slider("CDR Learning Rate (per doubling)", min_value=0.05, max_value=0.30,
                                      value=0.20, step=0.01)
conventional_learning_rate = st.sidebar.slider("Conventional Learning Rate (per doubling)", min_value=0.05,
                                               max_value=0.25, value=0.12, step=0.01)
scale_full_deployment_gt = st.sidebar.slider("Scale Damping Full-Scale Deployment (Gt)",
                                             min_value=10, max_value=50, value=45, step=5,
                                             help="Lower values scale faster; higher values scale slower")
max_cdr_capacity = st.sidebar.slider("Maximum CDR Capacity (GtCO2/year)",
                                     min_value=1, max_value=100, value=40, step=10,
                                     help="Hard physical cap on annual CDR sequestration")
damping_steepness = st.sidebar.slider("Sigmoid Damping Slope",
                                      min_value=2.0, max_value=20.0, value=8.0, step=0.5,
                                      help="Steeper values ramp scale/count and CDR learning faster around the midpoint")

st.sidebar.markdown("---")
st.sidebar.subheader("CDR Material Constraints")
cdr_material_budget_gt = st.sidebar.slider(
    "CDR Material Budget (Gt cumulative)",
    min_value=100, max_value=2000, value=500, step=100,
    help="Total CDR before material scarcity (limestone, energy, water) increases costs"
)
cdr_material_cost_multiplier = st.sidebar.slider(
    "CDR Material Cost Multiplier (max)",
    min_value=1.0, max_value=10.0, value=4.0, step=0.5,
    help="Maximum cost increase when CDR materials exhausted (4.0 = 4x base cost)"
)
cdr_material_capacity_floor = st.sidebar.slider(
    "CDR Material Capacity Floor",
    min_value=0.1, max_value=0.5, value=0.25, step=0.05,
    help="Minimum project initiation rate when materials exhausted (0.25 = 25%)"
)

st.sidebar.markdown("---")
enable_audits = st.sidebar.checkbox("Enable Audits", value=True)
random_seed = st.sidebar.number_input("Random Seed (0 = random)", min_value=0, max_value=10000, value=42)
monte_carlo_runs = st.sidebar.slider("Monte Carlo Runs", min_value=1, max_value=20, value=1, step=1,
                                     help="Number of ensemble runs (aggregates results when >1)")
st.sidebar.markdown("---")
st.sidebar.markdown("---")
# Remove Funding Mode Radio - we run both now.
 
run_button = st.sidebar.button("Run Simulation", type="primary", width='stretch')

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
    st.session_state.sim_xcr = None
    st.session_state.sim_govt = None
    st.session_state.agg = None

# Run simulation
if run_button:
    with st.spinner("Running scenarios..."):
        all_results = []
        base_seed = random_seed if random_seed > 0 else None
        
        for mode in ["XCR", "GOVT"]:
            dfs = []
            for i in range(monte_carlo_runs):
                if base_seed is not None:
                    np.random.seed(base_seed + i)
                sim = GCR_ABM_Simulation(years=years, enable_audits=enable_audits, price_floor=price_floor,
                                         adoption_rate=adoption_rate, inflation_target=inflation_target,
                                         xcr_start_year=xcr_start_year, years_to_full_capacity=years_to_full_capacity,
                                         cdr_learning_rate=cdr_learning_rate,
                                         conventional_learning_rate=conventional_learning_rate,
                                         scale_full_deployment_gt=scale_full_deployment_gt,
                                         damping_steepness=damping_steepness,
                                         max_cdr_capacity=max_cdr_capacity,
                                         bau_peak_year=bau_peak_year,
                                         cdr_material_budget_gt=cdr_material_budget_gt,
                                         cdr_material_cost_multiplier=cdr_material_cost_multiplier,
                                         cdr_material_capacity_floor=cdr_material_capacity_floor,
                                         funding_mode=mode)
                df_run = sim.run_simulation()
                df_run["run"] = i
                df_run["Scenario"] = "XCR Market" if mode == "XCR" else "Govt Funding"
                dfs.append(df_run)
                
                # Store first run for detailed viewing
                if i == 0:
                    if mode == "XCR":
                        st.session_state.sim_xcr = sim
                    else:
                        st.session_state.sim_govt = sim

            df_mode = pd.concat(dfs, ignore_index=True)
            df_mode["Year_Calendar"] = df_mode["Year"] + BASE_YEAR
            all_results.append(df_mode)

        df_combined = pd.concat(all_results, ignore_index=True)
        st.session_state.df = df_combined
        
        # Aggregation logic for multiple runs
        if monte_carlo_runs > 1:
            agg_results = []
            for scenario in ["XCR Market", "Govt Funding"]:
                df_scen = df_combined[df_combined["Scenario"] == scenario]
                agg = df_scen.groupby("Year").agg({
                    "CO2_ppm": ["mean", lambda x: x.quantile(0.1), lambda x: x.quantile(0.9)],
                    "BAU_CO2_ppm": "mean",
                    "Sequestration_Tonnes": "mean",
                    "CDR_Sequestration_Tonnes": "mean",
                    "Conventional_Mitigation_Tonnes": "mean",
                    "Avoided_Deforestation_Tonnes": "mean",
                    "Temperature_Anomaly": ["mean", lambda x: x.quantile(0.1), lambda x: x.quantile(0.9)],
                    "Inflation": "mean",
                    "Active_Countries": "mean",
                    "Projects_Operational": "mean",
                    "Market_Price": "mean",
                    "XCR_Supply": "mean",
                    "Annual_Gov_Spending": "mean",
                    "Gov_Brake_Factor": "mean",
                    "Gov_Debt_USD": "mean"
                })
                agg.columns = ["CO2_mean", "CO2_p10", "CO2_p90", "BAU_CO2_mean", "Seq_mean",
                               "CDR_seq_mean", "Conv_seq_mean", "AD_seq_mean",
                               "Temp_mean", "Temp_p10", "Temp_p90", "Inflation_mean",
                               "Countries_mean", "Projects_mean", "Price_mean", "Supply_mean",
                               "Gov_Spending_mean", "Gov_Brake_mean", "Gov_Debt_mean"]
                agg = agg.reset_index()
                agg["Scenario"] = scenario
                agg["Year_Calendar"] = agg["Year"] + BASE_YEAR
                agg_results.append(agg)
            st.session_state.agg = pd.concat(agg_results, ignore_index=True)
        else:
            st.session_state.agg = None

        st.success(f"Simulation complete! {years} years simulated for both XCR and Govt scenarios.")

# Display results if available
if st.session_state.df is not None:
    df_all = st.session_state.df
    agg = st.session_state.agg
    
    # Global multi-run flag
    multi_run = agg is not None
    
    # 📊 Global Scenario Comparison Metrics
    st.header("📊 Global Scenario Comparison")
    
    # Extract latest results for each scenario
    def get_scen_summary(scen_name):
        d = df_all[(df_all["Scenario"] == scen_name) & (df_all["run"] == 0)]
        return d.iloc[-1]

    s_xcr = get_scen_summary("XCR Market")
    s_govt = get_scen_summary("Govt Funding")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.subheader("CO2 (ppm)")
        st.metric("XCR Market", f"{s_xcr['CO2_ppm']:.1f}", delta=f"{s_xcr['CO2_ppm'] - 420:.1f}")
        st.metric("Govt Funding", f"{s_govt['CO2_ppm']:.1f}", delta=f"{s_govt['CO2_ppm'] - 420:.1f}")
        
    with col_m2:
        st.subheader("Inflation (%)")
        st.metric("XCR Market", f"{s_xcr['Inflation']*100:.2f}%", delta=f"{(s_xcr['Inflation']-inflation_target)*100:.2f}pp", delta_color="inverse")
        st.metric("Govt Funding", f"{s_govt['Inflation']*100:.2f}%", delta=f"{(s_govt['Inflation']-inflation_target)*100:.2f}pp", delta_color="inverse")

    with col_m3:
        st.subheader("Peak Inflation")
        p_xcr = df_all[df_all["Scenario"] == "XCR Market"]["Inflation"].max()
        p_govt = df_all[df_all["Scenario"] == "Govt Funding"]["Inflation"].max()
        st.metric("XCR Peak", f"{p_xcr*100:.2f}%")
        st.metric("Govt Peak", f"{p_govt*100:.2f}%")

    with col_m4:
        st.subheader("Fiscal Impact ($T)")
        st.metric("XCR QE", f"${s_xcr['CQE_Budget_Total']/1e12:.2f}T")
        st.metric("Govt Debt", f"${s_govt['Gov_Debt_USD']/1e12:.2f}T")

    st.markdown("---")

    # UI: Primary Tab Selection
    tab_scenario, tab_details = st.tabs(["📊 Scenario Comparison", "🔍 Scenario Details"])
    
    with tab_scenario:
        st.header("GCR Market vs. Government Funding")
        
        # Scenario Summary table - REMOVED, replaced by global metrics

        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            # CO2 Comparison
            fig_co2 = go.Figure()
            for scen in ["XCR Market", "Govt Funding"]:
                d_p = agg[agg["Scenario"] == scen] if multi_run else df_all[df_all["Scenario"] == scen]
                y_val = d_p["CO2_mean"] if multi_run else d_p["CO2_ppm"]
                fig_co2.add_trace(go.Scatter(x=d_p["Year_Calendar"], y=y_val, name=scen))
            fig_co2.update_layout(title="Atmospheric CO2 (ppm)", xaxis_title="Year", yaxis_title="ppm")
            st.plotly_chart(fig_co2, use_container_width=True)

        with col_c2:
            # Inflation Comparison
            fig_inf = go.Figure()
            for scen in ["XCR Market", "Govt Funding"]:
                d_p = agg[agg["Scenario"] == scen] if multi_run else df_all[df_all["Scenario"] == scen]
                y_val = d_p["Inflation_mean"] if multi_run else d_p["Inflation"]
                fig_inf.add_trace(go.Scatter(x=d_p["Year_Calendar"], y=y_val*100, name=scen))
            fig_inf.update_layout(title="Global Inflation (%)", xaxis_title="Year", yaxis_title="Inflation %")
            st.plotly_chart(fig_inf, use_container_width=True)

        col_c3, col_c4 = st.columns(2)
        with col_c3:
            # Sequestration Comparison
            fig_seq = go.Figure()
            for scen in ["XCR Market", "Govt Funding"]:
                d_p = agg[agg["Scenario"] == scen] if multi_run else df_all[df_all["Scenario"] == scen]
                y_val = d_p["Seq_mean"] if multi_run else d_p["Sequestration_Tonnes"]
                fig_seq.add_trace(go.Scatter(x=d_p["Year_Calendar"], y=y_val/1e9, name=scen))
            fig_seq.update_layout(title="Annual Sequestration (GtCO2)", xaxis_title="Year", yaxis_title="GtCO2/yr")
            st.plotly_chart(fig_seq, use_container_width=True)

        with col_c4:
            # Fiscal Comparison
            fig_fisc = go.Figure()
            # Govt Debt
            d_govt = agg[agg["Scenario"] == "Govt Funding"] if multi_run else df_all[df_all["Scenario"] == "Govt Funding"]
            y_govt = d_govt["Gov_Debt_mean"] if multi_run else d_govt["Gov_Debt_USD"]
            fig_fisc.add_trace(go.Scatter(x=d_govt["Year_Calendar"], y=y_govt/1e12, name="Govt Debt (Deficit)"))
            
            # XCR CQE
            d_xcr_full = df_all[(df_all["Scenario"] == "XCR Market") & (df_all["run"] == 0)]
            fig_fisc.add_trace(go.Scatter(x=d_xcr_full["Year_Calendar"], y=d_xcr_full["CQE_Budget_Total"]/1e12, name="XCR CQE Allocation"))
            
            fig_fisc.update_layout(title="Fiscal Commitment ($ Trillions)", xaxis_title="Year", yaxis_title="USD Trillions")
            st.plotly_chart(fig_fisc, use_container_width=True)

    with tab_details:
        st.header("🔍 Scenario Details")
        selected_scenario = st.selectbox("Select Scenario for detailed view", ["XCR Market", "Govt Funding"], index=0)
        
        df_single = df_all[(df_all["Scenario"] == selected_scenario) & (df_all["run"] == 0)]
        df_climate = agg[agg["Scenario"] == selected_scenario] if multi_run else df_single
        df = df_single  # Ensure df is defined for all sub-tabs
        
        # Select matching simulation object for details
        sim = st.session_state.sim_xcr if selected_scenario == "XCR Market" else st.session_state.sim_govt
        
        if sim is None:
            st.warning("Simulation data for this scenario is missing. Please run the simulation again.")
            st.stop()

        if multi_run:
            df_climate = df_climate.copy()
            df_climate["CO2_Avoided"] = df_climate["BAU_CO2_mean"] - df_climate["CO2_mean"]
            df_climate["CO2_ppm"] = df_climate["CO2_mean"]
            df_climate["BAU_CO2_ppm"] = df_climate["BAU_CO2_mean"]
        else:
            df_climate = df_single.copy()
            df_climate["CO2_Avoided"] = df_climate["BAU_CO2_ppm"] - df_climate["CO2_ppm"]

        # Summary Metrics - REMOVED, replaced by global metrics and detailed tab's own metrics below

        # Tabs for detailed views
        tab_cl, tab_econ, tab_mkt, tab_proj, tab_tech, tab_eq, tab_data = st.tabs([
            "🌡️ Climate & CO2",
            "💰 Economics",
            "📈 Market Dynamics",
            "🏗️ Projects",
            "🔬 Technology",
            "⚖️ Climate Equity",
            "📋 Data Table"
        ])

        # Tab 1: Climate & CO2
        with tab_cl:
            st.subheader("Atmospheric CO2 & Sequestration")

            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=("Atmospheric CO2 Concentration (GCR vs BAU)", "Annual Sequestration by Channel"),
                vertical_spacing=0.15,
                specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
            )

            df_tab = df_climate
            # BAU CO2 levels (Business As Usual - no intervention)
            fig.add_trace(
                go.Scatter(
                    x=df_tab['Year_Calendar'],
                    y=df_tab['BAU_CO2_ppm'],
                    name="BAU (No GCR)",
                    line=dict(color='#7f7f7f', width=2, dash='dot'),
                    fill='tozeroy',
                    fillcolor='rgba(127, 127, 127, 0.1)'
                ),
                row=1, col=1
            )

            # GCR CO2 levels (with optional quantile band)
            if multi_run and {"CO2_p10", "CO2_p90"}.issubset(df_tab.columns):
                fig.add_trace(
                    go.Scatter(
                        x=df_tab['Year_Calendar'],
                        y=df_tab['CO2_p90'],
                        name="CO2 90th",
                        line=dict(color='rgba(44,160,44,0.3)', width=0),
                        showlegend=False
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=df_tab['Year_Calendar'],
                        y=df_tab['CO2_p10'],
                        name="CO2 10-90%",
                        line=dict(color='rgba(44,160,44,0.3)', width=0),
                        fill='tonexty',
                        fillcolor='rgba(44,160,44,0.15)',
                        hoverinfo="skip",
                        showlegend=True,
                        legendgroup="CO2_band"
                    ),
                    row=1, col=1
                )
            fig.add_trace(
                go.Scatter(
                    x=df_tab['Year_Calendar'],
                    y=df_tab['CO2_ppm'],
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

            # Sequestration by channel (stacked)
            fig.add_trace(
                go.Bar(
                    x=df_tab['Year_Calendar'],
                    y=df_tab['CDR_Sequestration_Tonnes'] if not multi_run else df_tab['CDR_seq_mean'],
                    name="CDR",
                    marker_color='#1f77b4',
                    opacity=0.8
                ),
                row=2, col=1, secondary_y=False
            )
            fig.add_trace(
                go.Bar(
                    x=df_tab['Year_Calendar'],
                    y=df_tab['Conventional_Mitigation_Tonnes'] if not multi_run else df_tab['Conv_seq_mean'],
                    name="Conventional",
                    marker_color='#2ca02c',
                    opacity=0.7
                ),
                row=2, col=1, secondary_y=False
            )
            fig.add_trace(
                go.Bar(
                    x=df_tab['Year_Calendar'],
                    y=df_tab['Avoided_Deforestation_Tonnes'] if not multi_run else df_tab['AD_seq_mean'],
                    name="Avoided Deforestation",
                    marker_color='#8c564b',
                    opacity=0.7
                ),
                row=2, col=1, secondary_y=False
            )

            # Projects operational (secondary axis)
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df_single['Projects_Operational'],
                    name="Operational Projects",
                    line=dict(color='#ff7f0e', width=2, dash='dot'),
                    yaxis='y3'
                ),
                row=2, col=1,
                secondary_y=True
            )

            fig.update_xaxes(title_text="Calendar Year", row=2, col=1)
            fig.update_yaxes(title_text="CO2 (ppm)", row=1, col=1, range=[200, None])
            fig.update_yaxes(title_text="Tonnes CO2e/year", row=2, col=1, secondary_y=False)
            fig.update_yaxes(title_text="Project Count", row=2, col=1, secondary_y=True)

            fig.update_layout(height=700, showlegend=True, hovermode='x unified', barmode='stack')
            st.plotly_chart(fig, width='stretch')

            # BAU Impact Summary
            st.subheader("GCR Impact vs Business As Usual")
            col1, col2, col3 = st.columns(3)

            with col1:
                final_co2_avoided = df_climate.iloc[-1]['CO2_Avoided']
                st.metric("Final CO2 Avoided", f"{final_co2_avoided:.2f} ppm")

            with col2:
                if multi_run and "Seq_mean" in df_climate.columns:
                    total_sequestration = df_climate['Seq_mean'].sum()
                else:
                    total_sequestration = df_single['Sequestration_Tonnes'].sum()
                st.metric("Total Sequestration", f"{total_sequestration:.2e} tonnes")

            with col3:
                bau_growth = ((df_climate.iloc[-1]['BAU_CO2_ppm'] / 420.0) - 1) * 100
                st.metric("BAU CO2 Growth", f"+{bau_growth:.1f}%")
            col4, col5, col6 = st.columns(3)
            with col4:
                if multi_run and "CDR_seq_mean" in df_climate.columns:
                    cdr_total = df_climate['CDR_seq_mean'].sum()
                else:
                    cdr_total = df_single['CDR_Sequestration_Tonnes'].sum()
                st.metric("CDR Delivered", f"{cdr_total:.2e} tonnes")
            with col5:
                if multi_run and "Conv_seq_mean" in df_climate.columns:
                    conv_total = df_climate['Conv_seq_mean'].sum()
                else:
                    conv_total = df_single['Conventional_Mitigation_Tonnes'].sum()
                st.metric("Conventional Delivered", f"{conv_total:.2e} tonnes")
            with col6:
                if multi_run and "AD_seq_mean" in df_climate.columns:
                    ad_total = df_climate['AD_seq_mean'].sum()
                else:
                    ad_total = df_single['Avoided_Deforestation_Tonnes'].sum()
                st.metric("Avoided Deforestation Delivered", f"{ad_total:.2e} tonnes")

            # After climate view, use single-run dataframe for detailed tabs
            pass

        # Tab 2: XCR Economics
        with tab_econ:
            st.subheader("XCR Supply, Minting & Burning")

            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=(
                    "System Economics ($USD)",
                    "Economic Activity (Annual)",
                    "Cumulative Impact"
                ),
                vertical_spacing=0.12,
                specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}]]
            )

            # Labels depend on funding mode
            is_govt = df['Gov_Debt_USD'].max() > 0
            supply_label = "Gov Debt (USD)" if is_govt else "Total XCR Supply"
            supply_col = "Gov_Debt_USD" if is_govt else "XCR_Supply"
        
            # Calculate inflation-adjusted USD value (3% discount rate)
            if is_govt:
                df['Econ_Value_Adj'] = df['Gov_Debt_USD'] / (1.03 ** df['Year_Calendar'])
            else:
                df['Econ_Value_Adj'] = (df['XCR_Supply'] * df['Market_Price']) / (1.03 ** df['Year_Calendar'])
 
            # Primary axis: Supply or Debt
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df[supply_col],
                    name=supply_label,
                    line=dict(color='#1f77b4', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(31, 119, 180, 0.2)'
                ),
                row=1, col=1,
                secondary_y=False
            )

            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df['Econ_Value_Adj'],
                    name="Adj Economic Value (USD)",
                    line=dict(color='#ff7f0e', width=2, dash='dot'),
                ),
                row=1, col=1,
                secondary_y=True
            )

            # Economic activity (Minting/Spending)
            if is_govt:
                fig.add_trace(
                    go.Bar(
                        x=df['Year_Calendar'],
                        y=df['Annual_Gov_Spending'],
                        name="Annual Gov Spending",
                        marker_color='#d62728',  # Red for spending/debt
                        opacity=0.7
                    ),
                    row=2, col=1
                )
            else:
                fig.add_trace(
                    go.Bar(
                        x=df['Year_Calendar'],
                        y=df['XCR_Minted'],
                        name="XCR Minted",
                        marker_color='#2ca02c',
                        opacity=0.7
                    ),
                    row=2, col=1
                )

            # Burning (clawbacks - red bars, shown as negative)
            fig.add_trace(
                go.Bar(
                    x=df['Year_Calendar'],
                    y=-df['XCR_Burned_Annual'],  # Negative to show below axis
                    name="XCR Burned (Clawbacks)",
                    marker_color='#d62728',
                    opacity=0.7
                ),
                row=2, col=1
            )

            # Cumulative Impact (Burned or Debt growth)
            if is_govt:
                 fig.add_trace(
                    go.Scatter(
                        x=df['Year_Calendar'],
                        y=df['Gov_Debt_USD'],
                        name="Cumulative Gov Debt",
                        line=dict(color='#d62728', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(214, 39, 40, 0.2)'
                    ),
                    row=3, col=1
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=df['Year_Calendar'],
                        y=df['XCR_Burned_Cumulative'],
                        name="Cumulative XCR Burned",
                        line=dict(color='#d62728', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(214, 39, 40, 0.2)'
                    ),
                    row=3, col=1
                )

            fig.update_xaxes(title_text="Calendar Year", row=3, col=1)
            fig.update_yaxes(title_text="XCR Supply", row=1, col=1, secondary_y=False)
            fig.update_yaxes(title_text="USD Value (3% Adj)", row=1, col=1, secondary_y=True)
            fig.update_yaxes(title_text="XCR (Annual)", row=2, col=1)
            fig.update_yaxes(title_text="XCR Burned", row=3, col=1)

            fig.update_layout(height=900, showlegend=True, hovermode='x unified')
            st.plotly_chart(fig, width='stretch')

            # XCR Economics Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                total_minted = df['XCR_Minted'].sum()
                st.metric("Total XCR Minted", f"{total_minted:.2e}")
            with col2:
                total_burned = df.iloc[-1]['XCR_Burned_Cumulative']
                st.metric("Total XCR Burned", f"{total_burned:.2e}")
            with col3:
                burn_rate = (total_burned / total_minted * 100) if total_minted > 0 else 0
                st.metric("Burn Rate", f"{burn_rate:.1f}%")

        # Tab 3: Market Dynamics
        with tab_mkt:
            st.subheader("Market Price, Sentiment & Inflation")

            st.info("""
            **Capital Flows Chart (Bottom)**: Shows how private capital is attracted to XCR as a climate hedge.
            - **Forward Guidance** (orange dashed): Climate risk signal based on CO2 gap and progress
            - **Net Capital Flow** (green/red bars): Annual inflows (green) and outflows (red) in billions
            - **Cumulative Capital** (blue line): Net cumulative private investment in XCR
            - **Key Insight**: High inflation and climate urgency INCREASE XCR demand (real asset hedge)
            """)

            fig = make_subplots(
                rows=7, cols=1,
                subplot_titles=(
                    "XCR Market Price & Sentiment",
                    "Global Inflation Rate",
                    "Stability Ratio, CEA Warnings & CQE Utilization",
                    "System Capacity (Institutional Learning)",
                    "Private Capital Flows (Climate Hedge Demand)",
                    "Forward Guidance",
                    "CQE Interventions"
                ),
                vertical_spacing=0.07,
                specs=[
                    [{"secondary_y": True}],
                    [{"secondary_y": False}],
                    [{"secondary_y": True}],
                    [{"secondary_y": False}],
                    [{"secondary_y": True}],
                    [{"secondary_y": False}],
                    [{"secondary_y": False}],
                ]
            )

            # Price floor (area)
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
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
                    x=df['Year_Calendar'],
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
                    x=df['Year_Calendar'],
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
                    x=df['Year_Calendar'],
                    y=df['Inflation'] * 100,
                    name="Inflation (%)",
                    line=dict(color='#d62728', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(214, 39, 40, 0.1)'
                ),
                row=2, col=1
            )

            # CQE willingness center (sigmoid center at 1.5x target)
            inflation_brake_threshold = inflation_target * 1.5 * 100  # Convert to percentage
            fig.add_hline(
                y=inflation_brake_threshold,
                line_dash="dash",
                line_color="orange",
                annotation_text=f"CQE Willingness Center ({inflation_brake_threshold:.1f}%)",
                row=2, col=1
            )

            # Calculate Stability Ratio
            # Use dataframe column instead of sim object for robustness
            df['Stability_Ratio'] = (df['XCR_Supply'] * df['Market_Price']) / df['CQE_Budget_Total']

            # Stability Ratio
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
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

            # CQE budget utilization on secondary axis
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df['CQE_Budget_Utilization'],
                    name="CQE Budget Utilization",
                    line=dict(color='#8c564b', width=2, dash='dot'),
                ),
                row=3, col=1,
                secondary_y=True
            )
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=[0.9] * len(df),
                    name="Brake Start (90% cap)",
                    line=dict(color='#8c564b', width=1, dash='dash'),
                ),
                row=3, col=1,
                secondary_y=True
            )

            # Warning count on secondary axis
            df['Warning_Int'] = df['CEA_Warning'].astype(int)
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df['Warning_Int'],
                    name="Warning Status",
                    line=dict(color='red', width=1, dash='dot'),
                    fill='tozeroy',
                    fillcolor='rgba(255, 0, 0, 0.1)'
                ),
                row=3, col=1,
                secondary_y=True
            )

            # System Capacity (Institutional Learning)
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df['Capacity'],
                    name="System Capacity",
                    line=dict(color='#17becf', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(23, 190, 207, 0.3)'
                ),
                row=4, col=1
            )

            # Add reference line at 100% capacity
            fig.add_hline(
                y=1.0,
                line_dash="dash",
                line_color="green",
                annotation_text="Full Capacity",
                row=4, col=1
            )

            # Capital Flows (Net flows as bars, cumulative as line)
            # Separate into inflows and outflows for coloring
            df['Capital_Inflow'] = df['Net_Capital_Flow'].apply(lambda x: x if x > 0 else 0)
            df['Capital_Outflow'] = df['Net_Capital_Flow'].apply(lambda x: x if x < 0 else 0)

            # Inflows (green bars)
            fig.add_trace(
                go.Bar(
                    x=df['Year_Calendar'],
                    y=df['Capital_Inflow'] / 1e9,  # Convert to billions
                    name="Capital Inflow",
                    marker_color='#2ca02c',
                    opacity=0.7
                ),
                row=5, col=1,
                secondary_y=False
            )

            # Outflows (red bars)
            fig.add_trace(
                go.Bar(
                    x=df['Year_Calendar'],
                    y=df['Capital_Outflow'] / 1e9,  # Convert to billions
                    name="Capital Outflow",
                    marker_color='#d62728',
                    opacity=0.7
                ),
                row=5, col=1,
                secondary_y=False
            )

            # Net cumulative capital (line on secondary axis)
            df['Net_Capital_Cumulative'] = df['Capital_Inflow_Cumulative'] - df['Capital_Outflow_Cumulative']
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df['Net_Capital_Cumulative'] / 1e9,  # Convert to billions
                    name="Net Cumulative Capital",
                    line=dict(color='#1f77b4', width=3),
                ),
                row=5, col=1,
                secondary_y=True
            )

            # Forward guidance (own subplot)
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df['Forward_Guidance'],
                    name="Forward Guidance (Climate Risk)",
                    line=dict(color='#ff7f0e', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(255, 127, 14, 0.15)'
                ),
                row=6, col=1
            )

            fig.add_trace(
                go.Bar(
                    x=df['Year_Calendar'],
                    y=df['CQE_Spent'] / 1e9,  # trillions to billions
                    name="CQE Spent (USD B)",
                    marker_color='#9467bd',
                    opacity=0.7
                ),
                row=7, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=df['Year_Calendar'],
                    y=df['XCR_Purchased'] if 'XCR_Purchased' in df.columns else df['CQE_Spent'] / df['Price_Floor'],
                    name="XCR Purchased (approx)",
                    line=dict(color='#8c564b', width=2, dash='dot')
                ),
                row=7, col=1
            )

            fig.update_xaxes(title_text="Calendar Year", row=5, col=1)
            fig.update_yaxes(title_text="Price (USD)", row=1, col=1, secondary_y=False)
            fig.update_yaxes(title_text="Sentiment (0-1)", row=1, col=1, secondary_y=True)
            fig.update_yaxes(title_text="Inflation (%)", row=2, col=1)
            fig.update_yaxes(title_text="Stability Ratio", row=3, col=1, secondary_y=False)
            fig.update_yaxes(title_text="Warning (0/1)", row=3, col=1, secondary_y=True)
            fig.update_yaxes(title_text="Capacity (0-1)", row=4, col=1)
            fig.update_yaxes(title_text="Net Flow ($B/year)", row=5, col=1, secondary_y=False)
            fig.update_yaxes(title_text="Cumulative ($B) / Guidance", row=5, col=1, secondary_y=True)
            fig.update_yaxes(title_text="CQE Spend / XCR Bought", row=7, col=1)

            fig.update_layout(height=1300, showlegend=True, hovermode='x unified')
            st.plotly_chart(fig, width='stretch')

        # Tab 4: Projects
        with tab_proj:
            st.subheader("Project Portfolio Analysis")
            df_proj = df_single

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
                    x=df_proj['Year_Calendar'],
                    y=df_proj['Projects_Total'],
                    name="Total Projects",
                    line=dict(color='#1f77b4', width=2),
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df_proj['Year_Calendar'],
                    y=df_proj['Projects_Operational'],
                    name="Operational",
                    line=dict(color='#2ca02c', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(44, 160, 44, 0.2)'
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df_proj['Year_Calendar'],
                    y=df_proj['Projects_Development'],
                    name="In Development",
                    line=dict(color='#ff7f0e', width=2, dash='dot'),
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df_proj['Year_Calendar'],
                    y=df_proj['Projects_Failed'],
                    name="Failed",
                    line=dict(color='#d62728', width=2, dash='dash'),
                ),
                row=1, col=1
            )

            # Sequestration by year (bar chart)
            fig.add_trace(
                go.Bar(
                    x=df_proj['Year_Calendar'],
                    y=df_proj['Sequestration_Tonnes'],
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

            fig.update_xaxes(title_text="Calendar Year", row=1, col=1)
            fig.update_xaxes(title_text="Calendar Year", row=1, col=2)
            fig.update_yaxes(title_text="Project Count", row=1, col=1)
            fig.update_yaxes(title_text="Tonnes CO2e", row=1, col=2)

            fig.update_layout(height=700, showlegend=True)
            st.plotly_chart(fig, width='stretch')

            # Project statistics
            st.subheader("Project Statistics")
            col1, col2, col3, col4, col5 = st.columns(5)

            operational_projects = [p for p in sim.projects_broker.projects if p.status.value == "operational"]
            development_projects = [p for p in sim.projects_broker.projects if p.status.value == "development"]
            failed_projects = [p for p in sim.projects_broker.projects if p.status.value == "failed"]

            with col1:
                st.metric("Total Initiated", len(sim.projects_broker.projects))
            with col2:
                st.metric("Operational", len(operational_projects))
            with col3:
                st.metric("In Development", len(development_projects))
            with col4:
                st.metric("Failed", len(failed_projects))
            with col5:
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
                    x=df['Year_Calendar'],
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
                    x=df['Year_Calendar'],
                    y=df['CQE_Budget_Total'] / 1e12,  # Convert to trillions
                    name="CQE Budget",
                    line=dict(color='#2ca02c', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(44, 160, 44, 0.2)'
                ),
                row=1, col=2
            )

            fig.update_xaxes(title_text="Calendar Year", row=1, col=1)
            fig.update_xaxes(title_text="Calendar Year", row=1, col=2)
            fig.update_yaxes(title_text="Number of Countries", row=1, col=1)
            fig.update_yaxes(title_text="USD Trillions", row=1, col=2)

            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, width='stretch')

        # Tab 5: Technology Economics
        with tab_tech:
            st.subheader("Technology Learning & Policy Prioritization")

            # Explanatory info boxes
            st.info("""
            **Learning Curves**: Technology costs decrease as cumulative deployment grows. CDR has the
            steepest learning curve (20%) because it's early-stage, while conventional mitigation (12%)
            improves more slowly.
            """)

            st.warning("""
            **Policy Prioritization**: R multipliers are fixed at 1.0 per Chen (no time-shifted penalties).
            Prioritization comes from costs, capital availability, and capacity limits. R still scales rewards
            by cost-effectiveness relative to marginal CDR cost.
            """)

            st.error("""
            **Capacity Limits**: Conventional mitigation faces a hard-to-abate frontier. Availability tapers
            toward the frontier over time and floors at a residual tail rather than cutting off entirely.
            This shifts marginal growth to CDR as conventional potential saturates.
            """)

            # Chart A: Technology Cost Curves
            st.markdown("### Technology Cost Evolution (Learning Curves)")
            fig1 = go.Figure()

            fig1.add_trace(go.Scatter(
                x=df['Year_Calendar'], y=df['CDR_Cost_Per_Tonne'],
                name='CDR (20% LR)',
                line=dict(color='#d62728', width=3),
                mode='lines'
            ))
            fig1.add_trace(go.Scatter(
                x=df['Year_Calendar'], y=df['Conventional_Cost_Per_Tonne'],
                name='Conventional (12% LR)',
                line=dict(color='#2ca02c', width=3),
                mode='lines'
            ))
            fig1.update_layout(
                xaxis_title="Calendar Year",
                yaxis_title="Cost (USD/tonne CO2)",
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Chart B: Policy R-Multipliers Over Time
            st.markdown("### Policy R-Multipliers (Channel Prioritization)")
            fig2 = go.Figure()

            fig2.add_trace(go.Scatter(
                x=df['Year_Calendar'], y=df['CDR_Policy_Multiplier'],
                name='CDR',
                line=dict(color='#d62728', width=3),
                mode='lines'
            ))
            fig2.add_trace(go.Scatter(
                x=df['Year_Calendar'], y=df['Conventional_Policy_Multiplier'],
                name='Conventional',
                line=dict(color='#2ca02c', width=3),
                mode='lines'
            ))

            # Add annotations for eras
            fig2.add_annotation(x=20, y=1.8, text="Conventional Priority Era",
                               showarrow=False, font=dict(size=12, color='#2ca02c'))
            fig2.add_annotation(x=70, y=1.8, text="CDR Ramp-Up Era",
                               showarrow=False, font=dict(size=12, color='#d62728'))
            fig2.add_vline(x=45, line_dash="dash", line_color="gray", opacity=0.5)
            fig2.add_vline(x=55, line_dash="dash", line_color="gray", opacity=0.5)

            fig2.update_layout(
                xaxis_title="Calendar Year",
                yaxis_title="Policy Multiplier (applied to R-value)",
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Chart C: Channel Profitability Comparison
            st.markdown("### Channel Profitability (Revenue - Cost)")
            fig3 = go.Figure()

            fig3.add_trace(go.Scatter(
                x=df['Year_Calendar'], y=df['CDR_Profitability'],
                name='CDR',
                line=dict(color='#d62728', width=3),
                fill='tozeroy',
                mode='lines'
            ))
            fig3.add_trace(go.Scatter(
                x=df['Year_Calendar'], y=df['Conventional_Profitability'],
                name='Conventional',
                line=dict(color='#2ca02c', width=3),
                fill='tozeroy',
                mode='lines'
            ))

            fig3.add_hline(y=0, line_dash="dash", line_color="black",
                          annotation_text="Break-even")

            fig3.update_layout(
                xaxis_title="Calendar Year",
                yaxis_title="Profitability (USD/tonne)",
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig3, use_container_width=True)

            st.markdown("""
            **How to read profitability**: When a line crosses zero from below, that channel becomes
            economically viable and projects will initiate. Conventional is often profitable earlier
            due to lower costs, while CDR becomes viable as costs fall and conventional availability tapers.
            """)

            # Chart D: Conventional Capacity Constraint
            st.markdown("### Conventional Mitigation Capacity Availability (Tapered)")
            fig4 = go.Figure()

            fig4.add_trace(go.Scatter(
                x=df['Year_Calendar'],
                y=df['Conventional_Capacity_Factor'] * 100,
                name='Capacity Availability',
                line=dict(color='#2ca02c', width=3),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)',
                mode='lines'
            ))

            fig4.add_hline(
                y=10,
                line_dash="dash",
                line_color="gray",
                annotation_text="Residual floor (10%)",
                annotation_position="top right"
            )

            fig4.update_layout(
                xaxis_title="Calendar Year",
                yaxis_title="Capacity Availability (%)",
                yaxis_range=[0, 100],
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig4, use_container_width=True)

            st.markdown("""
            **Capacity taper explanation**: Conventional mitigation (solar, wind, efficiency) faces a
            hard-to-abate tail. Availability tapers down toward a residual floor rather than shutting
            off entirely, which keeps some conventional potential online while shifting marginal growth
            to CDR over time.
            """)

            # Summary statistics
            st.markdown("### Technology Transition Summary")
            col1, col2, col3 = st.columns(3)

            with col1:
                cdr_cost_reduction = ((df.iloc[0]['CDR_Cost_Per_Tonne'] - df.iloc[-1]['CDR_Cost_Per_Tonne'])
                                     / df.iloc[0]['CDR_Cost_Per_Tonne'] * 100)
                st.metric("CDR Cost Reduction", f"{cdr_cost_reduction:.1f}%",
                         delta=f"${df.iloc[0]['CDR_Cost_Per_Tonne']:.0f} → ${df.iloc[-1]['CDR_Cost_Per_Tonne']:.0f}/tonne")

            with col2:
                st.metric("Policy Multiplier (CDR)", f"{df.iloc[-1]['CDR_Policy_Multiplier']:.2f}",
                         delta="Fixed at 1.0")

            with col3:
                floor_threshold = df['Conventional_Capacity_Factor'].min() + 1e-6
                conv_floor_year = df[df['Conventional_Capacity_Factor'] <= floor_threshold].iloc[0]['Year_Calendar'] if len(df[df['Conventional_Capacity_Factor'] <= floor_threshold]) > 0 else "N/A"
                st.metric("Conventional Floor Reached", f"Year {conv_floor_year}",
                         delta="Residual availability floor")

        # Tab 6: Climate Equity
        with tab_eq:
            st.subheader("Climate Equity & Wealth Transfer Analysis")

            # Get equity summary
            equity = sim.get_equity_summary()

            # High-level summary
            st.markdown("### Global North vs Global South")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### OECD Countries (North)")
                st.metric("XCR Earned", f"{equity['oecd_earned']:.2e}")
                st.metric("XCR Purchased (CQE)", f"{equity['oecd_purchased']:.2e}")
                net_oecd = equity['oecd_net']
                st.metric("Net Position", f"{net_oecd:.2e}",
                         delta="surplus" if net_oecd > 0 else "deficit",
                         delta_color="normal" if net_oecd > 0 else "inverse")

            with col2:
                st.markdown("#### Non-OECD Countries (South)")
                st.metric("XCR Earned", f"{equity['non_oecd_earned']:.2e}")
                st.metric("XCR Purchased (CQE)", f"{equity['non_oecd_purchased']:.2e}")
                net_non_oecd = equity['non_oecd_net']
                st.metric("Net Position", f"{net_non_oecd:.2e}",
                         delta="surplus" if net_non_oecd > 0 else "deficit",
                         delta_color="normal" if net_non_oecd > 0 else "inverse")

            # Net transfer
            st.markdown("### Net Wealth Transfer")
            transfer = equity['net_transfer_to_south']
            direction = "North → South" if transfer > 0 else "South → North"
            transfer_usd = abs(transfer) * df.iloc[-1]['Market_Price']

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Net XCR Flow", f"{abs(transfer):.2e} XCR",
                         delta=direction)
            with col2:
                st.metric("USD Equivalent", f"${transfer_usd:.2e}",
                         delta=f"@ ${df.iloc[-1]['Market_Price']:.2f}/XCR")

            # Country-level details
            st.markdown("### Country-Level Net XCR Positions")
            country_df = pd.DataFrame(equity['country_details'])

            # Add formatted columns
            country_df['Net XCR (Earned - Purchased)'] = country_df['net_xcr'].apply(lambda x: f"{x:.2e}")
            country_df['OECD Status'] = country_df['oecd'].apply(lambda x: 'North' if x else 'South')
            country_df['Historical Emissions (GtCO2)'] = country_df['historical_emissions_gtco2']
            country_df['GDP (Tril USD)'] = country_df['gdp_tril']

            display_df = country_df[['country', 'OECD Status', 'Net XCR (Earned - Purchased)',
                                    'Historical Emissions (GtCO2)', 'GDP (Tril USD)']].copy()

            st.dataframe(display_df, use_container_width=True, height=400)

            st.markdown("""
            ---
            **Equity Mechanism Explanation**:

            The GCR system naturally creates wealth transfer from Global North to Global South through:

            1. **Historical Responsibility**: High-emission OECD countries contribute more CQE (buying XCR)
            2. **Project Distribution**: Global South has comparative advantage in CDR/nature-based projects
            3. **Project Geography**: CDR/nature-based projects predominantly in South

            **Result**: Natural wealth transfer from North to South for climate action.

            See `EQUITY_ANALYSIS.md` for detailed explanation.
            """)

        # Tab 7: Data Table
        with tab_data:
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
