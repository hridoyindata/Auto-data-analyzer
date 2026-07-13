# Auto Data Analyzer

A Streamlit app that cleans and analyses any CSV or Excel file automatically. Upload a file, the app fixes common data problems, then shows statistics, interactive charts and written findings. You can download the cleaned dataset at the end.

## Features

- Reads CSV and Excel (.xlsx) files
- Cleans the data automatically:
  - standardises column names
  - drops empty rows, empty columns and duplicate rows
  - converts text columns that are actually numbers (handles commas, $ and %)
  - detects date columns and converts them properly
  - fills missing numbers with the median and missing text with the most common value
- Cleaning report that lists every change made to the file
- Summary statistics for numeric and text columns
- Interactive charts: correlation heatmap, histograms, box plots, category breakdowns and trends over time
- Written insights: strong correlations, skewed columns, outliers and dominant categories
- Download button for the cleaned dataset

## Requirements

Python 3.10 or newer. Check with:

```
python --version
```

If you do not have Python, install it from python.org. On Windows, tick "Add Python to PATH" during the install.

## Setup on Windows

Open Command Prompt inside the project folder, then run these one at a time:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Setup on Mac or Linux

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```
streamlit run app.py
```

The app opens in your browser at http://localhost:8501. Press Ctrl+C in the terminal to stop it.

## How to use

1. Click "Browse files" and upload a CSV or Excel file. There is a sample_data.csv in this repo if you want to test it first.
2. Overview tab shows the cleaned data, row and column counts and column details.
3. Cleaning Report tab lists every change the app made to your file.
4. Statistics tab gives summary numbers for each column.
5. Charts tab has the heatmap, distributions, category breakdowns and time trends.
6. Insights tab gives written findings pulled from the data.
7. Download tab saves the cleaned file as a CSV.


## Built with

Python, Streamlit, Pandas, NumPy, Plotly
