# Overview

**Pakistan Flood Monitor** is a satellite-driven flood monitoring and early warning system designed for situational awareness across Pakistan's major river corridors.

## Core Objective

The system aims to combine free Earth Observation data (Sentinel-1, Sentinel-2, Landsat) with meteorological inputs (NASA POWER rainfall, Open-Meteo forecasts) to assess flood risk, identify inundated areas, and monitor infrastructure such as dams and embankments.

## Key Features

- **Public Dashboard**: A multi-page Streamlit application offering a complete view of live flood maps, historical data, and forecasts.
- **Spectral Water Detection**: Uses NDWI, MNDWI, and AWEI indices to analyze satellite imagery and detect water bodies. Replaces the prototype K-Means clustering method.
- **Dam-Aware Flood Risk**: Monitors upstream dam fills (including cross-border dams) via surface area proxies to modify downstream flood probability.
- **Flood Forecasting**: Integrates 14-day weather forecasts with a Model Leaderboard, comparing PyTorch LSTM against persistence and linear baselines.
- **Advanced SAR Analysis**: A simulated module demonstrating Synthetic Aperture Radar (SAR) signals to detect flood anomalies through cloud cover, combined with terrain height metrics (HAND).
- **Analyst Workflow**: A built-in lifecycle management system (draft -> review -> published) for flood event moderation.
- **NASA Hydromet Integration**: Pulls live precipitation data from NASA POWER.
- **Historical Backtesting**: An automated framework that replays 2010, 2014, and 2022 flood events to evaluate the system's detection capabilities.

## System Interfaces

1. **Streamlit UI (`streamlit_app.py`)**: The primary interface. It loads data from a CSV-backed backend service and provides a 15-page dashboard.
2. **Canonical FastAPI Backend (`pakistan_flood_monitor.api.main:app`)**: The supported runtime for programmatic access to internal monitoring endpoints and public feed data. It currently uses an in-memory data store for events and configurations.

## Limitations and Disclaimers

> **Limitations:** This system is built for situational awareness. The models and detection confidence scores are estimations based on heuristics and untrained baselines. Many features (like SAR and LSTM) are currently operational prototypes or simulations. This platform should **not** be used as the sole trigger for emergency evacuation. Always follow official instructions from local disaster management authorities like NDMA or PDMA.
