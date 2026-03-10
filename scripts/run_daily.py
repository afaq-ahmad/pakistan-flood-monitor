from pakistan_flood_monitor.pipeline.runner import FloodMonitoringPipeline


if __name__ == "__main__":
    report = FloodMonitoringPipeline().run_daily("Indus-Lower")
    print(report.model_dump_json(indent=2))
