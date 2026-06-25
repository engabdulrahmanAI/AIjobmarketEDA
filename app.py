import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="AI Jobs Market Dashboard",
    page_icon="🤖",
    layout="wide",
)

DATA_FILE = Path("ai_jobs_market_2025_2026 (1).csv")
REQUIRED_COLUMNS = [
    "job_title",
    "job_category",
    "experience_level",
    "years_of_experience",
    "education_required",
    "annual_salary_usd",
    "salary_min_usd",
    "salary_max_usd",
    "city",
    "country",
    "remote_work",
    "company_size",
    "industry",
    "required_skills",
    "demand_score",
    "benefits_score_10",
    "salary_tier",
]


def money(value: float) -> str:
    return f"${value:,.0f}"


@st.cache_data(show_spinner=False)
def read_csv(file_or_path):
    return pd.read_csv(file_or_path)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df_clean = df.copy()

    numeric_columns = [
        "years_of_experience",
        "annual_salary_usd",
        "salary_min_usd",
        "salary_max_usd",
        "demand_score",
        "benefits_score_10",
    ]
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    if {"salary_max_usd", "salary_min_usd"}.issubset(df_clean.columns):
        df_clean["salary_range_usd"] = (
            df_clean["salary_max_usd"] - df_clean["salary_min_usd"]
        )

    return df_clean


def validate_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in REQUIRED_COLUMNS if col not in df.columns]


def load_data_section():
    st.sidebar.header("📁 Dataset")
    uploaded_file = st.sidebar.file_uploader(
        "Upload AI jobs CSV file",
        type=["csv"],
        help="ارفع ملف ai_jobs_market_2025_2026 CSV إذا ما كان موجود داخل المشروع.",
    )

    if uploaded_file is not None:
        return read_csv(uploaded_file), "Uploaded CSV file"

    if DATA_FILE.exists():
        return read_csv(DATA_FILE), str(DATA_FILE)

    st.info(
        "ارفع ملف CSV من القائمة الجانبية، أو أضف الملف داخل GitHub بنفس الاسم: "
        "`ai_jobs_market_2025_2026 (1).csv`."
    )
    return None, None


def add_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Filters")

    filtered = df.copy()

    filter_columns = {
        "country": "Country",
        "experience_level": "Experience Level",
        "job_category": "Job Category",
        "remote_work": "Remote Work",
        "company_size": "Company Size",
        "salary_tier": "Salary Tier",
    }

    for col, label in filter_columns.items():
        if col in filtered.columns:
            options = sorted(filtered[col].dropna().astype(str).unique())
            selected = st.sidebar.multiselect(label, options, default=options)
            if selected:
                filtered = filtered[filtered[col].astype(str).isin(selected)]

    if "annual_salary_usd" in filtered.columns and not filtered["annual_salary_usd"].dropna().empty:
        min_salary = int(filtered["annual_salary_usd"].min())
        max_salary = int(filtered["annual_salary_usd"].max())
        salary_range = st.sidebar.slider(
            "Annual Salary USD",
            min_value=min_salary,
            max_value=max_salary,
            value=(min_salary, max_salary),
            step=1000,
        )
        filtered = filtered[
            filtered["annual_salary_usd"].between(salary_range[0], salary_range[1])
        ]

    return filtered


def show_overview(df: pd.DataFrame):
    st.subheader("1. Dataset Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{df.shape[0]:,}")
    col2.metric("Columns", f"{df.shape[1]:,}")
    col3.metric("Missing Values", f"{int(df.isna().sum().sum()):,}")
    col4.metric("Duplicates", f"{int(df.duplicated().sum()):,}")

    with st.expander("Preview dataset"):
        st.dataframe(df.head(20), use_container_width=True)

    with st.expander("Column names"):
        st.write(list(df.columns))

    with st.expander("Missing values by column"):
        missing = df.isna().sum().reset_index()
        missing.columns = ["Column", "Missing Values"]
        st.dataframe(missing, use_container_width=True)


def show_key_metrics(df: pd.DataFrame):
    st.subheader("2. Key Salary Metrics")

    if "annual_salary_usd" not in df.columns or df.empty:
        st.warning("No salary column available after filtering.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Salary", money(df["annual_salary_usd"].mean()))
    col2.metric("Median Salary", money(df["annual_salary_usd"].median()))
    col3.metric("Minimum Salary", money(df["annual_salary_usd"].min()))
    col4.metric("Maximum Salary", money(df["annual_salary_usd"].max()))


def show_top_jobs(df: pd.DataFrame):
    st.subheader("3. Top 10 AI Job Titles")

    if "job_title" not in df.columns:
        st.warning("Column `job_title` is missing.")
        return

    top_jobs = df["job_title"].value_counts().head(10).reset_index()
    top_jobs.columns = ["Job Title", "Number of Jobs"]

    fig = px.bar(
        top_jobs,
        x="Number of Jobs",
        y="Job Title",
        orientation="h",
        title="Top 10 Most Common AI Job Titles",
        text="Number of Jobs",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top_jobs, use_container_width=True)


def show_salary_distribution(df: pd.DataFrame):
    st.subheader("4. Salary Distribution")

    if "annual_salary_usd" not in df.columns:
        st.warning("Column `annual_salary_usd` is missing.")
        return

    fig = px.histogram(
        df,
        x="annual_salary_usd",
        nbins=30,
        marginal="box",
        title="Distribution of Annual AI Salaries",
        labels={"annual_salary_usd": "Annual Salary USD"},
    )
    st.plotly_chart(fig, use_container_width=True)


def show_salary_by_experience(df: pd.DataFrame):
    st.subheader("5. Salary by Experience Level")

    needed = {"experience_level", "annual_salary_usd"}
    if not needed.issubset(df.columns):
        st.warning("Required columns are missing for this section.")
        return

    salary_by_experience = (
        df.groupby("experience_level")["annual_salary_usd"]
        .agg(count="count", mean="mean", median="median", min="min", max="max")
        .sort_values(by="mean", ascending=False)
        .round(2)
    )
    st.dataframe(salary_by_experience, use_container_width=True)

    avg_exp = salary_by_experience.reset_index().sort_values("mean")
    fig = px.bar(
        avg_exp,
        x="experience_level",
        y="mean",
        title="Average Annual Salary by Experience Level",
        labels={"experience_level": "Experience Level", "mean": "Average Salary USD"},
        text="mean",
    )
    st.plotly_chart(fig, use_container_width=True)

    fig_box = px.box(
        df,
        x="experience_level",
        y="annual_salary_usd",
        title="Annual Salary by Experience Level",
        labels={
            "experience_level": "Experience Level",
            "annual_salary_usd": "Annual Salary USD",
        },
    )
    st.plotly_chart(fig_box, use_container_width=True)


def show_country_salary(df: pd.DataFrame):
    st.subheader("6. Top Countries by Average Salary")

    needed = {"country", "annual_salary_usd"}
    if not needed.issubset(df.columns):
        st.warning("Required columns are missing for this section.")
        return

    country_salary = (
        df.groupby("country")["annual_salary_usd"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    country_salary.columns = ["Country", "Average Salary USD"]

    fig = px.bar(
        country_salary,
        x="Average Salary USD",
        y="Country",
        orientation="h",
        title="Top 10 Countries by Average AI Salary",
        text="Average Salary USD",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(country_salary.round(2), use_container_width=True)


def show_salary_range(df: pd.DataFrame):
    st.subheader("7. Salary Range")

    if "salary_range_usd" not in df.columns:
        st.warning("Salary range could not be created because salary min/max columns are missing.")
        return

    col1, col2 = st.columns(2)
    col1.metric("Average Salary Range", money(df["salary_range_usd"].mean()))
    col2.metric("Median Salary Range", money(df["salary_range_usd"].median()))

    preview_columns = ["salary_min_usd", "salary_max_usd", "salary_range_usd"]
    st.dataframe(df[preview_columns].head(20), use_container_width=True)

    fig = px.histogram(
        df,
        x="salary_range_usd",
        nbins=30,
        title="Distribution of Salary Range",
        labels={"salary_range_usd": "Salary Range USD"},
    )
    st.plotly_chart(fig, use_container_width=True)


def show_final_insights():
    st.subheader("8. Final Insights")
    st.markdown(
        """
        - The AI jobs market contains different job titles, categories, experience levels, countries, company sizes, and salary tiers.
        - Average annual salary is high, but salaries vary based on job title, country, company size, remote work type, and required skills.
        - Years of experience alone does not fully explain salary differences.
        - Salary should be analyzed together with job category, country, company size, and remote work.
        - This dataset provides useful insights into AI job market trends for 2025–2026.
        """
    )


def main():
    st.title("🤖 AI Jobs Market 2025–2026 Dashboard")
    st.caption("Streamlit dashboard based on your EDA notebook")

    df, source = load_data_section()
    if df is None:
        st.stop()

    missing_columns = validate_columns(df)
    if missing_columns:
        st.error("The uploaded CSV is missing required columns:")
        st.write(missing_columns)
        st.stop()

    df_clean = clean_data(df)
    filtered_df = add_sidebar_filters(df_clean)

    st.sidebar.success(f"Loaded from: {source}")
    st.sidebar.write(f"Filtered rows: {filtered_df.shape[0]:,}")

    if filtered_df.empty:
        st.warning("No data after applying filters. Change the filters from the sidebar.")
        st.stop()

    show_overview(filtered_df)
    show_key_metrics(filtered_df)
    show_top_jobs(filtered_df)
    show_salary_distribution(filtered_df)
    show_salary_by_experience(filtered_df)
    show_country_salary(filtered_df)
    show_salary_range(filtered_df)
    show_final_insights()

    csv_buffer = io.StringIO()
    filtered_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Download filtered data as CSV",
        data=csv_buffer.getvalue(),
        file_name="filtered_ai_jobs_market.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
