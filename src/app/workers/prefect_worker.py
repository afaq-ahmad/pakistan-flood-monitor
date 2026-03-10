from app.pipelines import preprocess_sar_pipeline


def run_prefect_wrapper() -> str:
    return preprocess_sar_pipeline()
