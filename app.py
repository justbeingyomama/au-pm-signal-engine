import streamlit as st
import pandas as pd
from sheets.client import SheetsClient
from models import Signal

# --- Page Configuration ---
st.set_page_config(
    page_title="AU PM Signal Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #00F0FF;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #FFFFFF;
        margin-bottom: 0;
    }
    .metric-label {
        color: #A0A0A0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .high-priority {
        background-color: rgba(255, 75, 75, 0.1);
        border-left: 3px solid #ff4b4b;
        padding: 5px 10px;
        border-radius: 4px;
    }
    .status-badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
    }
    .status-new { background-color: rgba(0, 240, 255, 0.2); color: #00F0FF; }
    .status-notified { background-color: rgba(0, 255, 0, 0.2); color: #00FF00; }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=300)
def load_data():
    """Load data from Google Sheets into a Pandas DataFrame."""
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        sheet_id = st.secrets["SPREADSHEET_ID"]

        client = SheetsClient(creds_info, sheet_id)
        rows = client.get_all_signal_rows()

        if not rows:
            return pd.DataFrame()

        columns = [
            "ID", "Dedupe Hash", "Source", "Type", "Company",
            "Role", "Location", "URL", "Date", "Discovered Date",
            "Score", "High Priority", "Remote Likelihood", "Raw Text", "Notes", "Status"
        ]

        df = pd.DataFrame(rows, columns=columns)

        df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        df = df.sort_values(by=["Date", "Score"], ascending=[False, False])
        return df

    except Exception as e:
        st.error("Failed to connect to Google Sheets.")
        st.exception(e)
        return pd.DataFrame()

# --- Main App ---
def main():
    st.title("🚀 AU PM Signal Engine")
    st.markdown("Automated intelligence for Product Management hiring signals in Australia.")

    df = load_data()

    if df.empty:
        st.info("No signals found in the database yet. The engine might still be collecting data.")
        return

    # --- Sidebar Filters ---
    st.sidebar.header("Filter Signals")

    search_query = st.sidebar.text_input("Search Roles or Companies...")

    sources = ["All"] + list(df["Source"].unique())
    selected_source = st.sidebar.selectbox("Source", sources)

    min_score = st.sidebar.slider("Minimum Relevance Score", 0, 10, 0)

    remote_only = st.sidebar.checkbox("Remote/Hybrid Only", value=False)

    show_historical = st.sidebar.checkbox("Show previously notified roles", value=True)

    # --- Apply Filters ---
    filtered_df = df.copy()

    if search_query:
        search_mask = (
            filtered_df["Role"].str.contains(search_query, case=False, na=False) |
            filtered_df["Company"].str.contains(search_query, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]

    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["Source"] == selected_source]

    filtered_df = filtered_df[filtered_df["Score"] >= min_score]

    if remote_only:
        filtered_df = filtered_df[
            filtered_df["Remote Likelihood"].isin(["High", "Medium"]) |
            filtered_df["Location"].str.contains("Remote|Anywhere", case=False, na=False)
        ]

    if not show_historical:
        filtered_df = filtered_df[filtered_df["Status"] == "New"]

    # --- Metrics Dashboard ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">Total Signals</p>
            <p class="metric-value">{len(df)}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        top_tier = len(df[df["Score"] >= 8])
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">Top Tier (Score 8+)</p>
            <p class="metric-value">{top_tier}</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        remote_count = len(df[df["Remote Likelihood"] == "High"])
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">Highly Remote</p>
            <p class="metric-value">{remote_count}</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        new_leads = len(df[df["Status"] == "New"])
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">Actionable (New)</p>
            <p class="metric-value">{new_leads}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Data Display ---
    st.subheader(f"Matching Results ({len(filtered_df)})")

    display_cols = ["Role", "Company", "Location", "Score", "Remote Likelihood", "Date", "Source", "URL"]
    display_df = filtered_df[display_cols].copy()

    def make_clickable(url):
        return f'<a target="_blank" href="{url}">Link</a>' if pd.notna(url) and url else ""

    display_df["URL"] = display_df["URL"].apply(make_clickable)
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")

    st.write(
        display_df.to_html(escape=False, index=False, classes=["table", "table-striped"]),
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
