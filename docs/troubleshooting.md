# Troubleshooting Guide

This document outlines common issues encountered during local development and usage of the Pakistan Flood Monitor, along with their resolutions.

## 1. Streamlit Dashboard Issues

### Symptom: `FileNotFoundError` when loading dashboard
**Cause**: The local data directories or CSV files have not been generated, or the `data/` and `storage/` folders are missing.
**Fix**: Ensure you have created the storage directories. If mock data is missing, run the application once which should trigger default data fallbacks, or ensure `data/corridors.csv` exists based on the repository defaults.

### Symptom: NASA Hydromet Page Shows Empty Data / Fails
**Cause**: The NASA POWER API might be rate-limiting you, or your NASA Earthdata credentials in `.env.local` are incorrect.
**Fix**: 
1. Check `.env.local` for `NASA_EARTHDATA_USERNAME` and `NASA_BEARER_TOKEN`.
2. Ensure you have authorized the application via Earthdata login.
3. Check terminal logs for `401 Unauthorized` or `429 Too Many Requests`.

### Symptom: Dashboard is Very Slow to Load
**Cause**: Streamlit re-renders the UI on every interaction. If caching (`@st.cache_data`) is bypassed, it fetches live satellite metadata synchronously.
**Fix**: Do not disable Streamlit caching in development unless actively debugging a service. Ensure external API calls are wrapped in caching decorators.

## 2. ML & Satellite Pipeline Issues

### Symptom: Sentinel-2 Images Not Downloading
**Cause**: The Earth Search STAC API might be down, or the bounding box requested has 100% cloud cover.
**Fix**: 
1. Check the target coordinates for the corridor in `satellite_ml_service.py`.
2. The system has heuristic fallbacks to bypass STAC failures. Check the terminal logs to see if a `Fallback` was triggered.

### Symptom: SAR Analysis or Forecasts Return 0.0
**Cause**: The SAR and advanced ML modules currently use simulated/mock data structures for demonstration. If they fail, they return zeros or empty arrays.
**Fix**: This is expected behavior for the prototype. Check `advanced_ml_service.py` to trace the simulation logic.

## 3. FastAPI Backend Issues

### Symptom: "Draft" Events Disappear After Restart
**Cause**: The FastAPI application uses an in-memory dictionary to store events.
**Fix**: This is an architectural limitation of the current prototype. Any restart of `uvicorn` will flush the state. Future iterations will include a PostgreSQL database.

### Symptom: `401 Unauthorized` on `/internal` API Routes
**Cause**: Missing or incorrect Bearer token.
**Fix**: Pass the `Authorization: Bearer <token>` header with the exact string defined in your `.env.local` for `FLOOD_MONITOR_ADMIN_TOKEN` or `FLOOD_MONITOR_ANALYST_TOKEN`.
