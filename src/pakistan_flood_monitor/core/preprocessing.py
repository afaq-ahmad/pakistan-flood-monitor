from dataclasses import dataclass


@dataclass
class PreprocessingOutput:
    scene_id: str
    calibrated: bool
    cloud_masked: bool
    terrain_corrected: bool


class Preprocessor:
    def preprocess_sar(self, scene_id: str) -> PreprocessingOutput:
        return PreprocessingOutput(scene_id=scene_id, calibrated=True, cloud_masked=False, terrain_corrected=True)

    def preprocess_optical(self, scene_id: str) -> PreprocessingOutput:
        return PreprocessingOutput(scene_id=scene_id, calibrated=False, cloud_masked=True, terrain_corrected=False)
