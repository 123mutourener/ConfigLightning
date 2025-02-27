import os.path

from PIL import Image
from torchvision.transforms import Compose
from customise_pl.transforms import CommonCompose
from customise_pl.transforms import init_transforms
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader, Dataset, random_split
from glob import glob
import torch


class XJ3SegmentDataModule(LightningDataModule):
    def __init__(self, data_root, image_folder="images", mask_folder="masks", batch_size=4, num_workers=8,
                 pin_memory=True, split_portion=(0.7, 0.15, 0.15), subset_portion=1,
                 train_image_transform=None,
                 train_common_transform=None,
                 valid_image_transform=None,
                 valid_common_transform=None,
                 test_image_transform=None,
                 test_common_transform=None):
        super().__init__()
        self.train_files = None
        self.test_files = None
        self.valid_files = None
        self.train_names = None
        self.image_path = None
        self.mask_path = None
        self.data_root = data_root
        self.image_folder = image_folder
        self.mask_folder = mask_folder
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.pin_memory = pin_memory
        self.split_portion = split_portion
        self.train_image_transform = Compose(init_transforms(train_image_transform))
        self.train_common_transform = CommonCompose(init_transforms(train_common_transform))
        self.test_image_transform = Compose(init_transforms(test_image_transform))
        self.test_common_transform = CommonCompose(init_transforms(test_common_transform))
        self.subset_portion = subset_portion

        if valid_image_transform is None:
            self.valid_image_transform = Compose(init_transforms(test_image_transform))
        else:
            self.valid_image_transform = Compose(init_transforms(valid_image_transform))
        if valid_common_transform is None:
            self.valid_common_transform = CommonCompose(init_transforms(test_common_transform))
        else:
            self.valid_common_transform = CommonCompose(init_transforms(valid_common_transform))

    def prepare_data(self):
        # download, split, etc...
        # only called on 1 GPU/TPU in distributed
        pass

    def setup(self, stage):
        # make assignments here ``'fit'``, ``'validate'``, ``'test'``, or ``'predict'``, include transforms and dataset
        # called on every process in DDP
        self.image_path = os.path.join(self.data_root, self.image_folder)
        self.mask_path = os.path.join(self.data_root, self.mask_folder)
        files_all = [os.path.basename(file)[:-4] for file in glob(os.path.join(self.mask_path, "*.png"))]
        files_all = files_all[: int(len(files_all) * self.subset_portion)]
        self.split_portion = [int(len(files_all) * portion) for portion in self.split_portion]
        self.split_portion[-1] += len(files_all) - sum(self.split_portion)
        splitted_sets = random_split(files_all, self.split_portion,
                                     generator=torch.Generator().manual_seed(42))
        if len(splitted_sets) == 2:
            self.train_files, self.valid_files = splitted_sets
        elif len(splitted_sets) == 3:
            self.train_files, self.valid_files, self.test_files = splitted_sets

    def train_dataloader(self):
        train_split = MaskSegmentDataset(self.train_files, self.data_root, self.image_folder, self.mask_folder,
                                         image_transform=self.train_image_transform,
                                         common_transform=self.train_common_transform)
        return DataLoader(train_split, batch_size=self.batch_size, num_workers=self.num_workers,
                          pin_memory=self.pin_memory)

    def val_dataloader(self):
        val_split = MaskSegmentDataset(self.valid_files, self.data_root, self.image_folder, self.mask_folder,
                                       image_transform=self.valid_image_transform,
                                       common_transform=self.valid_common_transform)
        return DataLoader(val_split, batch_size=self.batch_size, num_workers=self.num_workers,
                          pin_memory=self.pin_memory)

    def test_dataloader(self):
        test_split = MaskSegmentDataset(self.test_files, self.data_root, self.image_folder, self.mask_folder,
                                        image_transform=self.test_image_transform,
                                        common_transform=self.test_common_transform)
        return DataLoader(test_split, batch_size=self.batch_size, num_workers=self.num_workers,
                          pin_memory=self.pin_memory)

    def teardown(self, stage):
        # clean up after fit or test
        # called on every process in DDP
        pass


class MaskSegmentDataset(Dataset):
    CLASSES = ["鱼骨线",
               "车道线-普通车道线_清晰_被遮挡"]

    def __init__(self, image_files, data_root, image_folder="images", mask_folder="masks", image_transform=None,
                 common_transform=None):
        super().__init__()
        self.image_files = image_files
        self.data_root = data_root
        self.image_folder = image_folder
        self.mask_folder = mask_folder
        self.image_transform = image_transform
        self.common_transform = common_transform

    def __getitem__(self, index):
        img_path = os.path.join(self.data_root, self.image_folder, self.image_files[index] + ".jpg")
        mask_path = os.path.join(self.data_root, self.mask_folder, self.image_files[index] + ".png")
        image = Image.open(img_path).convert('RGB')
        mask = Image.open(mask_path)

        if self.image_transform is not None:
            image = self.image_transform(image)
        if self.common_transform is not None:
            image, mask = self.common_transform(image, mask)
        return image, mask

    def __len__(self):
        return len(self.image_files)
