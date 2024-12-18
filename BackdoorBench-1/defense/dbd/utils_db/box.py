
'''

code: 
'''
import os 
import sys


sys.path.append('../')
sys.path.append(os.getcwd())
import numpy as np
import torch
# from data.utils import (
#     get_transform,
#     get_semi_idx,
# )
from defense.dbd.data.prefetch import PrefetchLoader

from utils.aggregate_block.dataset_and_transform_generate import get_transform_self

from model.utils import (
    get_network_dbd,
    load_state,
    get_criterion,
    get_network,
    get_optimizer,
    get_saved_epoch,
    get_scheduler,
)

from model.model import SelfModel, LinearModel
from data.dataset import PoisonLabelDataset, SelfPoisonDataset, MixMatchDataset
#from utils.bd_dataset import prepro_cls_DatasetBD
from utils.nCHW_nHWC import nCHW_to_nHWC

def get_information(args,result,config_ori):
    config = config_ori
    # pre_transform = get_transform(config["transform"]["pre"])
    # # train_primary_transform = get_transform(config["transform"]["train"]["primary"])
    # # train_remaining_transform = get_transform(config["transform"]["train"]["remaining"])
    # # train_transform = {
    # #     "pre": pre_transform,
    # #     "primary": train_primary_transform,
    # #     "remaining": train_remaining_transform,
    # # }
    # # logger.info("Training transformations:\n {}".format(train_transform))
    # aug_primary_transform = get_transform(config["transform"]["aug"]["primary"])
    # aug_remaining_transform = get_transform(config["transform"]["aug"]["remaining"])
    # aug_transform = {
    #     "pre": pre_transform,
    #     "primary": aug_primary_transform,
    #     "remaining": aug_remaining_transform,
    # }
    aug_transform = get_transform_self(args.dataset, *([args.input_height,args.input_width]) , train = True, prefetch =args.prefetch)
    # logger.info("Augmented transformations:\n {}".format(aug_transform))
    # logger.info("Load dataset from: {}".format(config["dataset_dir"]))
    # clean_train_data = get_dataset(config["dataset_dir"], train_transform)
    # poison_train_idx = gen_poison_idx(clean_train_data, target_label, poison_ratio)
    # poison_idx_path = os.path.join(args.saved_dir, "poison_idx.npy")
    # np.save(poison_idx_path, poison_train_idx)
    # logger.info("Save poisoned index to {}".format(poison_idx_path))
    # poison_train_data = PoisonLabelDataset(
    #     clean_train_data, bd_transform, poison_train_idx, target_label
    # )
    x = result['bd_train']['x']
    y = result['bd_train']['y']
    # data_set = torch.utils.data.TensorDataset(x,y)
    # dataset = prepro_cls_DatasetBD(
    #     full_dataset_without_transform=data_set,
    #     poison_idx=np.zeros(len(data_set)),  # one-hot to determine which image may take bd_transform
    #     bd_image_pre_transform=None,
    #     bd_label_pre_transform=None,
    #     ori_image_transform_in_loading=transform,
    #     ori_label_transform_in_loading=None,
    #     add_details_in_preprocess=False,
    # )
    self_poison_train_data = SelfPoisonDataset(x,y, aug_transform,args)
    # if args.distributed:
    #     self_poison_train_sampler = DistributedSampler(self_poison_train_data)
    #     batch_size = int(config["loader"]["batch_size"])
    #     num_workers = config["loader"]["num_workers"]
    #     self_poison_train_loader = get_loader(
    #         self_poison_train_data,
    #         batch_size=batch_size,
    #         sampler=self_poison_train_sampler,
    #         num_workers=num_workers,
    #     )
    # else:
        # self_poison_train_sampler = None
    self_poison_train_loader_ori = torch.utils.data.DataLoader(self_poison_train_data, batch_size=args.batch_size_self, num_workers=args.num_workers,drop_last=False, shuffle=True,pin_memory=True)
    if args.prefetch:
        self_poison_train_loader = PrefetchLoader(self_poison_train_loader_ori, self_poison_train_data.mean, self_poison_train_data.std)
    else:
        self_poison_train_loader = self_poison_train_loader_ori
    # self_poison_train_loader = get_loader(
    #         self_poison_train_data, config["loader"], shuffle=True
    #     )

    #logger.info("\n===Setup training===")
    backbone = get_network_dbd(args)
    #logger.info("Create network: {}".format(config["network"]))
    self_model = SelfModel(backbone)
    self_model = self_model.to(args.device)
    # if args.distributed:
    #     # Convert BatchNorm*D layer to SyncBatchNorm before wrapping Network with DDP.
    #     if config["sync_bn"]:
    #         self_model = nn.SyncBatchNorm.convert_sync_batchnorm(self_model)
    #         logger.info("Turn on synchronized batch normalization in ddp.")
    #     self_model = nn.parallel.DistributedDataParallel(self_model, device_ids=[gpu])
    criterion = get_criterion(config["criterion"])
    criterion = criterion.to(args.device)
    #logger.info("Create criterion: {}".format(criterion))
    optimizer = get_optimizer(self_model, config["optimizer"])
    #logger.info("Create optimizer: {}".format(optimizer))
    scheduler = get_scheduler(optimizer, config["lr_scheduler"])
    #logger.info("Create scheduler: {}".format(config["lr_scheduler"]))
    resumed_epoch = load_state(
        self_model, args.resume, args.checkpoint_load, 0, optimizer, scheduler,
    )
    box = {
      'self_poison_train_loader': self_poison_train_loader,
      'self_model': self_model,
      'criterion': criterion,
      'optimizer': optimizer,
      'scheduler': scheduler,
      'resumed_epoch': resumed_epoch
    }
    return box

'''
note: 
def get_information(args,result,config_ori)主要完成了以下任务：

数据预处理和增强: 从配置文件config_ori中获取数据增强（augmentation）的转换信息，并使用这些信息来创建aug_transform。这是为了在训练过程中对数据进行各种转换，例如旋转、裁剪等，以增加模型的泛化能力。
创建训练数据集：使用预处理和增强的转换函数以及输入的高度和宽度，从原始数据集中创建训练数据。这部分代码也处理了如何从保存的索引文件中加载毒药标签的索引。
模型定义：定义了一个名为SelfModel的模型，该模型基于backbone网络。
训练设置：定义了损失函数（criterion）、优化器（optimizer）和学习率调度器（scheduler）。
加载模型状态：如果指定了恢复训练的选项（resume），则从指定的路径加载模型的权重和训练状态。
返回结果：最后，返回一个包含训练数据加载器、模型、损失函数、优化器、学习率调度器和恢复的epoch数的字典。
总的来说，这段代码主要是为了设置一个带有毒药标签的数据集的训练环境，包括数据预处理、模型定义、训练设置和状态恢复等步骤。
'''
