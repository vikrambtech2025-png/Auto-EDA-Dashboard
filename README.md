---
title: Auto EDA Dashboard
emoji: ":bar_chart:"
colorFrom: teal
colorTo: amber
sdk: docker
app_port: 7860
pinned: false
---

# Auto EDA Dashboard

## Project Description
This project provides an automated Exploratory Data Analysis (EDA) dashboard, designed to quickly generate insights from various datasets. It supports uploading CSV, XLS, and XLSX files and provides a comprehensive report including data quality, distributions, correlations, and categorical breakdowns.

## Features
- **Automated EDA**: Generates detailed data profiles with minimal user input.
- **File Uploads**: Supports CSV, XLS, and XLSX file formats.
- **Persistent Dataset Run History**: Keeps track of previously analyzed datasets.
- **Automated Data Quality Score**: Provides a score based on missing values, duplicates, etc.
- **Missing Value Analysis**: Identifies and quantifies missing data.
- **Duplicate Row Detection**: Helps in cleaning data by finding duplicate entries.
- **Semantic Type Inference**: Automatically detects data types.
- **Numeric Summaries**: Provides descriptive statistics, quantiles, skew, and IQR outlier detection.
- **Top Category Summaries**: Summarizes categorical features.
- **Pearson Correlation Ranking**: Ranks correlations between numerical variables.
- **Canvas-based Dashboard Charts**: Visualizes key data insights.
- **JSON Report Export**: Allows exporting the generated EDA report.
- **Deployment Configurations**: Includes Docker, Render, and Railway deployment configs.

## Setup and Installation

### Prerequisites
- Python 3.8+
- pip (Python package installer)
- Docker (for Docker deployment)

### Clone the Repository
```bash
git clone https://github.com/vikrambtech2025-png/Auto-EDA-Dashboard.git
cd Auto-EDA-Dashboard
```

### Create a Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Running the Application

### Local Run

If you are using a fresh Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your web browser.

### Docker Run

```powershell
docker compose up --build
```

Open `http://127.0.0.1:8000`.

## Deployment

### Render

1. Push this folder to a GitHub repository.
2. Create a new Render Blueprint from the repository.
3. Render will read `render.yaml`, build the Docker image, mount persistent storage at `/app/data`, and expose the web service.

### Railway

1. Push this folder to a GitHub repository.
2. Create a Railway project from the repository.
3. Railway will use `railway.json` and the Dockerfile.
4. Add a persistent volume mounted to `/app/data` if you want uploaded files and SQLite history to survive redeploys.

## Usage
1. Navigate to the application in your web browser.
2. Upload your dataset (CSV, XLS, or XLSX).
3. The dashboard will automatically generate and display the EDA report.

## Notes
SQLite is configured with WAL mode and is efficient for this application profile: report metadata, generated EDA JSON, and upload history. For a multi-user SaaS version, the next database step is PostgreSQL with object storage for uploaded files.

## Contributing
Contributions are welcome! Please feel free to open issues or submit pull requests.

## License
This project is licensed under the MIT License.
