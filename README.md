10x Genomics: Financial Data Pipeline & AI Analytics
# 10x Genomics: Financial Data Pipeline & AI Analytics

## Project Overview
This project is an end-to-end data engineering and analytics pipeline focused on the financial health of 10x Genomics. It transforms raw financial statements into a structured data warehouse, visualized through an interactive dashboard, and features a custom AI chatbot for financial querying.

## Tech Stack
* **Data Engineering:** Python (Pandas, SQLAlchemy)
* **Database:** SQL Server (T-SQL, Star Schema)
* **Business Intelligence:** Power BI (DAX)
* **AI Integration:** Python Chatbot

## Repository Structure
* `/notebooks`: Contains the ETL pipeline (`staging`, `cleaning`, and `data_warehouse` Jupyter notebooks).
* `/databases`: Contains the SQL Server `.bak` files representing the three stages of the database architecture.
* `/dashboard`: Contains the Power BI file (`.pbix`) tracking liquidity, profitability, and growth.
* `/chatbot`: Contains the Python script for the interactive financial assistant.

## Methodology
1. **Staging:** Raw financial data was ingested into SQL Server using Python.
2. **Cleaning:** Data was unpivoted from a "wide" to "long" format, standardized, and cleansed of metadata.
3. **Data Warehouse:** A Star Schema was designed to optimize the data for high-performance BI reporting.
