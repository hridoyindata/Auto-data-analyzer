import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

MISSING_TOKENS = ["", "nan", "NaN", "None", "none", "NULL", "null", "-", "N/A", "n/a", "NA", "<NA>"]
DATE_HINTS = ("date", "time", "day", "month", "year", "created", "updated", "dob", "timestamp")


def load_file(file):
    if file.name.lower().endswith(".csv"):
        try:
            return pd.read_csv(file)
        except UnicodeDecodeError:
            file.seek(0)
            return pd.read_csv(file, encoding="latin-1")
    return pd.read_excel(file)


def strip_symbols(series):
    return (
        series.str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("%", "", regex=False)
    )


def clean_data(raw):
    df = raw.copy()
    report = []

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    report.append("Standardised column names to lowercase with underscores")

    rows_before, cols_before = df.shape
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if rows_before - df.shape[0]:
        report.append(f"Dropped {rows_before - df.shape[0]} completely empty row(s)")
    if cols_before - df.shape[1]:
        report.append(f"Dropped {cols_before - df.shape[1]} completely empty column(s)")

    dupes = int(df.duplicated().sum())
    if dupes:
        df = df.drop_duplicates().reset_index(drop=True)
        report.append(f"Removed {dupes} duplicate row(s)")

    for col in df.select_dtypes(include=["object", "string"]).columns:
        stripped = df[col].astype(str).str.strip()
        df[col] = stripped.mask(stripped.isin(MISSING_TOKENS))

        non_null = df[col].dropna()
        if non_null.empty:
            continue

        as_numbers = pd.to_numeric(strip_symbols(non_null), errors="coerce")
        if as_numbers.notna().mean() >= 0.9:
            df[col] = pd.to_numeric(strip_symbols(df[col]), errors="coerce")
            report.append(f"Converted '{col}' from text to numbers")
            continue

        if any(hint in col for hint in DATE_HINTS):
            as_dates = pd.to_datetime(non_null, errors="coerce", dayfirst=True)
            if as_dates.notna().mean() >= 0.9:
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                report.append(f"Converted '{col}' to dates")

    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        if n_missing == 0:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].median())
            report.append(f"Filled {n_missing} missing value(s) in '{col}' with the median")
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            report.append(f"Left {n_missing} missing date(s) in '{col}' blank instead of guessing")
        else:
            mode = df[col].mode()
            fill_value = mode.iloc[0] if not mode.empty else "unknown"
            df[col] = df[col].fillna(fill_value)
            report.append(f"Filled {n_missing} missing value(s) in '{col}' with the most common value ('{fill_value}')")

    if len(report) == 1:
        report.append("No other issues found, the data was already in good shape")

    return df, report


def count_outliers(series):
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((series < lower) | (series > upper)).sum())


def build_insights(df):
    insights = []
    numeric = df.select_dtypes(include="number")
    text_cols = df.select_dtypes(include=["object", "string"]).columns

    if numeric.shape[1] >= 2:
        corr = numeric.corr()
        best = None
        cols = corr.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                value = corr.iloc[i, j]
                if pd.notna(value) and (best is None or abs(value) > abs(best[2])):
                    best = (cols[i], cols[j], value)
        if best and abs(best[2]) >= 0.5:
            direction = "positive" if best[2] > 0 else "negative"
            insights.append(
                f"'{best[0]}' and '{best[1]}' have a strong {direction} correlation of {best[2]:.2f}"
            )

    for col in numeric.columns:
        skew = numeric[col].skew()
        if pd.notna(skew) and abs(skew) > 1:
            if skew > 0:
                insights.append(f"'{col}' is right skewed, most values are low with a few large ones pulling the average up")
            else:
                insights.append(f"'{col}' is left skewed, most values are high with a few small ones pulling the average down")

    for col in numeric.columns:
        n_out = count_outliers(numeric[col].dropna())
        if n_out:
            insights.append(f"'{col}' has {n_out} outlier(s) based on the IQR rule, worth checking if these are real values or entry errors")

    for col in text_cols:
        counts = df[col].value_counts()
        if len(counts) > 1 and len(df) > 0:
            share = counts.iloc[0] / len(df)
            if share >= 0.7:
                insights.append(f"'{col}' is dominated by '{counts.index[0]}' which covers {share:.0%} of all rows")
        if df[col].nunique() == len(df) and len(df) > 10:
            insights.append(f"'{col}' has a different value in every row, it looks like an ID column")

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            dates = df[col].dropna()
            if not dates.empty:
                insights.append(f"'{col}' covers {dates.min().date()} to {dates.max().date()}")

    if not insights:
        insights.append("Nothing unusual stood out in this dataset")

    return insights


def main():
    st.set_page_config(page_title="Auto Data Analyzer", page_icon="📊", layout="wide")

    st.title("Auto Data Analyzer")
    st.write("Upload a CSV or Excel file. The app cleans it, runs the analysis and shows the results.")

    uploaded = st.file_uploader("Choose a file", type=["csv", "xlsx"])

    if uploaded is None:
        st.info("Waiting for a file.")
        st.stop()

    try:
        raw = load_file(uploaded)
    except Exception as error:
        st.error(f"Could not read the file: {error}")
        st.stop()

    if raw.empty:
        st.error("The file has no data in it.")
        st.stop()

    df, report = clean_data(raw)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

    tab_overview, tab_cleaning, tab_stats, tab_charts, tab_insights, tab_download = st.tabs(
        ["Overview", "Cleaning Report", "Statistics", "Charts", "Insights", "Download"]
    )

    with tab_overview:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rows", f"{df.shape[0]:,}")
        m2.metric("Columns", df.shape[1])
        m3.metric("Numeric columns", len(numeric_cols))
        m4.metric("Text columns", len(text_cols))

        st.subheader("Cleaned data preview")
        st.dataframe(df.head(50))

        st.subheader("Column details")
        details = pd.DataFrame(
            {
                "column": df.columns,
                "type": [str(t) for t in df.dtypes],
                "unique_values": [df[c].nunique() for c in df.columns],
                "missing": [int(df[c].isna().sum()) for c in df.columns],
            }
        )
        st.dataframe(details)

        with st.expander("Original data before cleaning"):
            st.dataframe(raw.head(50))

    with tab_cleaning:
        st.subheader("Changes made to your data")
        for item in report:
            st.write("- " + item)
        st.write(f"Shape before: {raw.shape[0]} rows x {raw.shape[1]} columns")
        st.write(f"Shape after: {df.shape[0]} rows x {df.shape[1]} columns")

        missing_raw = raw.isna().sum()
        missing_raw = missing_raw[missing_raw > 0]
        if not missing_raw.empty:
            st.subheader("Missing values in the original file")
            fig = px.bar(
                x=missing_raw.index.astype(str),
                y=missing_raw.values,
                labels={"x": "column", "y": "missing values"},
            )
            st.plotly_chart(fig)

    with tab_stats:
        if numeric_cols:
            st.subheader("Numeric summary")
            st.dataframe(df[numeric_cols].describe().T.round(2))
        if text_cols:
            st.subheader("Text column summary")
            summary = pd.DataFrame(
                {
                    "column": text_cols,
                    "unique_values": [df[c].nunique() for c in text_cols],
                    "most_common": [
                        df[c].mode().iloc[0] if not df[c].mode().empty else "" for c in text_cols
                    ],
                }
            )
            st.dataframe(summary)
        if not numeric_cols and not text_cols:
            st.write("No numeric or text columns found to summarise.")

    with tab_charts:
        if len(numeric_cols) >= 2:
            st.subheader("Correlation heatmap")
            corr = df[numeric_cols].corr().round(2)
            fig = px.imshow(
                corr, text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto"
            )
            st.plotly_chart(fig)

        if numeric_cols:
            st.subheader("Distribution")
            chosen_numeric = st.selectbox("Pick a numeric column", numeric_cols)
            left, right = st.columns(2)
            with left:
                st.plotly_chart(px.histogram(df, x=chosen_numeric, nbins=30))
            with right:
                st.plotly_chart(px.box(df, y=chosen_numeric))

        if text_cols:
            st.subheader("Category breakdown")
            chosen_text = st.selectbox("Pick a text column", text_cols)
            counts = df[chosen_text].value_counts().head(10)
            fig = px.bar(
                x=counts.values,
                y=counts.index.astype(str),
                orientation="h",
                labels={"x": "count", "y": chosen_text},
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig)

        if date_cols and numeric_cols:
            st.subheader("Trend over time")
            pick1, pick2, pick3 = st.columns(3)
            chosen_date = pick1.selectbox("Date column", date_cols)
            chosen_value = pick2.selectbox("Value column", numeric_cols)
            chosen_agg = pick3.selectbox("Aggregation", ["sum", "mean", "count"])
            trend = (
                df.dropna(subset=[chosen_date])
                .groupby(chosen_date)[chosen_value]
                .agg(chosen_agg)
                .reset_index()
            )
            st.plotly_chart(px.line(trend, x=chosen_date, y=chosen_value, markers=True))

    with tab_insights:
        st.subheader("Automatic findings")
        for line in build_insights(df):
            st.write("- " + line)

    with tab_download:
        st.subheader("Cleaned dataset")
        st.dataframe(df.head(50))
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download cleaned CSV",
            data=csv_bytes,
            file_name="cleaned_data.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
