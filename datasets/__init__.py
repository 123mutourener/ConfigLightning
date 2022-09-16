from .xj3segment import XJ3SegmentDataModule

__all__ = {"XJ3SegmentDataModule": XJ3SegmentDataModule}


def get_dataset(dataset_name):
    assert dataset_name in __all__, f"The dataset {dataset_name} is not supported!"
    return __all__[dataset_name]
