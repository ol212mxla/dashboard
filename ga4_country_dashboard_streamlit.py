
# GA4 Country Performance Dashboard (Streamlit) - Patched
# ---------------------------------------------------
# How to run locally:
#   1) pip install -r requirements.txt
#   2) streamlit run ga4_country_dashboard_streamlit.py
#
# The app expects a CSV with the columns found in your uploaded file:
# Country, Active users, New users, Returning users, Engaged sessions,
# Average engagement time per active user, Bounce rate, Add to carts,
# Checkouts, Ecommerce purchases, Items purchased, Total revenue

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Geographic Details Dashboard for Maxfield Marketing",
    layout="wide",
    page_icon=":bar_chart:"
)

@st.cache_data
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    # Clean revenue to numeric
    if "Total revenue" in df.columns:
        df["Total revenue (num)"] = (
            df["Total revenue"]
            .astype(str)
            .str.replace(r"[^0-9.\-]", "", regex=True)
            .replace("", np.nan)
            .astype(float)
        )
    else:
        df["Total revenue (num)"] = 0.0

    # Normalize column names (strip, lower) and keep originals
    df.columns = [c.strip() for c in df.columns]

    # Precompute useful metrics
    # Safety against divide-by-zero
    df["AOV"] = np.where(df["Ecommerce purchases"].replace(0, np.nan).notna(),
                         df["Total revenue (num)"] / df["Ecommerce purchases"].replace(0, np.nan),
                         np.nan)

    df["Revenue / Active User"] = np.where(df["Active users"]>0,
                                           df["Total revenue (num)"] / df["Active users"],
                                           np.nan)

    # Funnel rates
    df["ATC rate"] = np.where(df["Active users"]>0,
                              df["Add to carts"] / df["Active users"],
                              np.nan)
    df["Checkout rate (from ATC)"] = np.where(df["Add to carts"]>0,
                                              df["Checkouts"] / df["Add to carts"],
                                              np.nan)
    df["Purchase rate (from Checkout)"] = np.where(df["Checkouts"]>0,
                                                   df["Ecommerce purchases"] / df["Checkouts"],
                                                   np.nan)
    df["Units per order"] = np.where(df["Ecommerce purchases"]>0,
                                     df["Items purchased"] / df["Ecommerce purchases"],
                                     np.nan)

    # Ensure numeric types
    numeric_cols = [
        "Active users","New users","Returning users","Engaged sessions",
        "Average engagement time per active user","Bounce rate","Add to carts",
        "Checkouts","Ecommerce purchases","Items purchased","Total revenue (num)",
        "AOV","Revenue / Active User","ATC rate","Checkout rate (from ATC)",
        "Purchase rate (from Checkout)","Units per order"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

st.title("GA4 Country Performance Dashboard")
st.caption("Interactive insights for audience, engagement, funnel, revenue, and geography.")

# File input
st.sidebar.header("Upload Data")
uploaded = st.sidebar.file_uploader("Upload GA4 country CSV", type=["csv"])
st.sidebar.markdown("Or use the sample file if you already have the provided CSV.")

# Filters
st.sidebar.header("Filters")
default_top_n = 10
top_n = st.sidebar.slider("Top N Countries (by Active Users)", 3, 30, default_top_n, step=1)

if uploaded is None:
    st.info("Please upload your CSV to begin.")
    st.stop()

df = load_data(uploaded)

# Country filter
all_countries = sorted(df["Country"].unique().tolist())
selected_countries = st.sidebar.multiselect("Countries", all_countries, default=all_countries)
df = df[df["Country"].isin(selected_countries)].copy()

# --------------------
# KPI Header
# --------------------
total_active = int(df["Active users"].sum())
total_new = int(df["New users"].sum())
total_returning = int(df["Returning users"].sum())
total_revenue = float(df["Total revenue (num)"].sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Users", f"{total_active:,}")
col2.metric("New Users", f"{total_new:,}")
col3.metric("Returning Users", f"{total_returning:,}")
col4.metric("Total Revenue", f"${total_revenue:,.2f}")

st.divider()

# --------------------
# Section 1: Audience Overview
# --------------------
st.subheader("1) Audience Overview")
top_df = df.sort_values("Active users", ascending=False).head(top_n)

a1, a2 = st.columns([2, 1])
with a1:
    fig_users = px.bar(
        top_df,
        x="Country",
        y="Active users",
        title=f"Top {min(top_n, len(top_df))} Countries by Active Users",
        text="Active users"
    )
    fig_users.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_users.update_layout(yaxis_title="Active Users", xaxis_title="Country")
    st.plotly_chart(fig_users, use_container_width=True)

with a2:
    st.markdown("**New vs Returning Users**")
    nr_df = top_df.melt(id_vars=["Country"], value_vars=["New users","Returning users"],
                        var_name="User Type", value_name="Users")
    fig_nr = px.bar(
        nr_df, x="Country", y="Users", color="User Type",
        barmode="stack", title="New vs Returning (Top Countries)"
    )
    st.plotly_chart(fig_nr, use_container_width=True)

st.divider()

# --------------------
# Section 2: Engagement Quality
# --------------------
st.subheader("2) Engagement Quality")
st.caption("Bounce rate vs. average engagement time, bubble size = active users")

fig_eng = px.scatter(
    df,
    x="Bounce rate",
    y="Average engagement time per active user",
    size="Active users",
    hover_name="Country",
    title="Engagement: Bounce Rate vs. Avg Engagement Time",
)
fig_eng.update_layout(xaxis_tickformat=".0%", xaxis_title="Bounce Rate",
                      yaxis_title="Avg Engagement Time per Active User (sec or min)")
st.plotly_chart(fig_eng, use_container_width=True)

st.divider()

# --------------------
# Section 3: Conversion Funnel
# --------------------
st.subheader("3) Conversion Funnel")
st.caption("Add to carts → Checkouts → Purchases → Units per order")

# Funnel (counts) for selected countries aggregated
agg_counts = {
    "Add to carts": df["Add to carts"].sum(),
    "Checkouts": df["Checkouts"].sum(),
    "Ecommerce purchases": df["Ecommerce purchases"].sum(),
}
funnel_df = pd.DataFrame({
    "Step": list(agg_counts.keys()),
    "Count": list(agg_counts.values())
})

fig_funnel = px.funnel(funnel_df, x="Count", y="Step", title="Global Funnel (Selected Countries)")
st.plotly_chart(fig_funnel, use_container_width=True)

# Rates table by country
rate_cols = ["ATC rate","Checkout rate (from ATC)","Purchase rate (from Checkout)","Units per order"]
show_cols = ["Country","Active users","Add to carts","Checkouts","Ecommerce purchases","Items purchased"] + rate_cols
st.markdown("**Funnel KPIs by Country**")
st.dataframe(
    df[show_cols].sort_values("Active users", ascending=False).reset_index(drop=True),
    use_container_width=True
)

st.divider()

# --------------------
# Section 4: Revenue & Monetization
# --------------------
st.subheader("4) Revenue & Monetization")

r1, r2 = st.columns([2, 1])
with r1:
    fig_rev = px.bar(
        df.sort_values("Total revenue (num)", ascending=False).head(top_n),
        x="Country",
        y="Total revenue (num)",
        title=f"Top {top_n} Countries by Revenue",
        text="Total revenue (num)"
    )
    fig_rev.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig_rev.update_layout(yaxis_title="Total Revenue (USD)", xaxis_title="Country")
    st.plotly_chart(fig_rev, use_container_width=True)

with r2:
    st.markdown("**AOV & Revenue per User (Top Countries)**")
    monet_df = df.sort_values("Total revenue (num)", ascending=False).head(top_n)
    monet_df = monet_df.assign(
        **{
            "AOV ($)": monet_df["AOV"],
            "Revenue per Active User ($)": monet_df["Revenue / Active User"]
        }
    )
    fig_monet = px.bar(
        monet_df.melt(id_vars=["Country"], value_vars=["AOV ($)","Revenue per Active User ($)"],
                      var_name="Metric", value_name="Value"),
        x="Country", y="Value", color="Metric", barmode="group",
        title="AOV vs Revenue per Active User"
    )
    st.plotly_chart(fig_monet, use_container_width=True)

# Revenue share treemap (robust implementation)
st.markdown("**Revenue Share by Country**")
try:
    import plotly.graph_objects as go
    treemap_df = df[["Country", "Total revenue (num)"]].copy()
    treemap_df["Total revenue (num)"] = treemap_df["Total revenue (num)"].fillna(0)

    fig_tree = go.Figure(
        go.Treemap(
            labels=treemap_df["Country"],
            parents=[""] * len(treemap_df),
            values=treemap_df["Total revenue (num)"],
            branchvalues="total"
        )
    )
    fig_tree.update_layout(title="Revenue Share")
    st.plotly_chart(fig_tree, use_container_width=True)

except Exception as e:
    st.warning(f"Treemap failed to render (falling back to bar chart). Error: {e}")
    fig_rev_fallback = px.bar(
        df.sort_values("Total revenue (num)", ascending=False),
        x="Country", y="Total revenue (num)",
        title="Revenue Share (Fallback)",
        text="Total revenue (num)"
    )
    fig_rev_fallback.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    st.plotly_chart(fig_rev_fallback, use_container_width=True)

st.divider()

# --------------------
# Choropleth: Users by Geography
# --------------------
st.subheader("Geography: Active Users by Country")
st.caption("Hover for values. Location mode uses country names.")

fig_map = px.choropleth(
    df,
    locations="Country",
    locationmode="country names",
    color="Active users",
    hover_name="Country",
    title="Active Users by Country",
    color_continuous_scale=px.colors.sequential.Blues
)
st.plotly_chart(fig_map, use_container_width=True)

st.write("")
st.info("Tip: Use the sidebar to filter countries and adjust the Top N.")
