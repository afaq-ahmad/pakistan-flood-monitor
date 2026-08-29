# Contributing Guidelines

Thank you for your interest in contributing to the Pakistan Flood Monitor. This project aims to provide free, open-source flood situational awareness using Earth Observation data.

## AI Agent Operating Contract

AI coding agents must read and follow the repository-wide [`AGENTS.md`](../AGENTS.md) before
planning or changing files. It defines the canonical package, environmental-data integrity,
CRS/unit handling, provenance, human decision gates, testing, scope, and pull-request evidence
required for every agent-authored task. At task start, also read the concise
[`IMPLEMENTATION_STATUS.md`](engineering/IMPLEMENTATION_STATUS.md) ledger and applicable
[architecture decision records](adr/README.md). The contract supplements this human contribution
guide and the accepted architecture decision records.

## Getting Started

1. Fork the repository.
2. Follow the [Local Setup Guide](setup.md) to get the project running locally.
3. Create a new branch for your feature or bugfix (`git checkout -b feature/your-feature-name`).

## Coding Standards

- **Python**: Use Python 3.10+.
- **Typing**: Use standard Python type hinting for function signatures (`def my_func(param: str) -> dict:`).
- **Docstrings**: Document the purpose, arguments, and return types of all complex ML or data service functions.
- **Dependencies**: Keep dependencies lightweight. Do not add heavy ML frameworks (like TensorFlow or massive pre-trained weights) unless discussed in an issue first.

## Submitting Changes

1. Ensure your code passes all local tests by running `python -m pytest tests/ -v`.
2. If you add new data services or ML logic, write corresponding unit tests.
3. Submit a Pull Request with a clear description of the problem solved or the feature added.
4. Do not include API keys, passwords, or `.env` files in your commits.

## Documentation

If your feature changes how the system operates, please update the relevant documentation in the `docs/` folder. All documentation should follow plain language, use Mermaid diagrams for architecture, and avoid pasting raw source code in Markdown files.

## Adding New Rivers or Dams

If you are a domain expert and wish to add new corridors or dams:
1. Dam records are located in `src/pakistan_flood_monitor/services/dam_service.py`.
2. Corridor bounding boxes are located in `satellite_ml_service.py`.
3. Please include coordinates and references to official sources (like WAPDA) when contributing physical infrastructure data.
