# ---------------------------------------------------------------------
# Project "Track 3D-Objects Over Time"
# Copyright (C) 2020, Dr. Antje Muntzinger / Dr. Andreas Haja.
#
# Purpose of this file : Detect 3D objects in lidar point clouds using deep learning
#
# You should have received a copy of the Udacity license together with this program.
#
# https://www.udacity.com/course/self-driving-car-engineer-nanodegree--nd013
# ----------------------------------------------------------------------
#

# general package imports
import numpy as np
import torch
from easydict import EasyDict as edict

# add project directory to python path to enable relative imports
import os
import sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

# model-related
from tools.objdet_models.resnet.models import fpn_resnet
from tools.objdet_models.resnet.utils.evaluation_utils import decode, post_processing 

from tools.objdet_models.darknet.models.darknet2pytorch import Darknet as darknet
from tools.objdet_models.darknet.utils.evaluation_utils import post_processing_v2


# load model-related parameters into an edict
def load_configs_model(model_name='darknet', configs=None):

    # init config file, if none has been passed
    if configs==None:
        configs = edict()  

    # get parent directory of this file to enable relative paths
    curr_path = os.path.dirname(os.path.realpath(__file__))
    parent_path = configs.model_path = os.path.abspath(os.path.join(curr_path, os.pardir))    
    
    # set parameters according to model type
    if model_name == "darknet":
        configs.model_path = os.path.join(parent_path, 'tools', 'objdet_models', 'darknet')
        configs.pretrained_filename = os.path.join(configs.model_path, 'pretrained', 'complex_yolov4_mse_loss.pth')
        configs.arch = 'darknet'
        configs.batch_size = 4
        configs.cfgfile = os.path.join(configs.model_path, 'config', 'complex_yolov4.cfg')
        configs.conf_thresh = 0.5
        configs.distributed = False
        configs.img_size = 608
        configs.nms_thresh = 0.4
        configs.num_samples = None
        configs.num_workers = 4
        configs.pin_memory = True
        configs.use_giou_loss = False
        configs.min_iou = 0.5  # minimum intersection over union for a valid detection

    elif model_name == 'fpn_resnet':
        configs.model_path = os.path.join(parent_path, 'tools', 'objdet_models', 'resnet')
        configs.pretrained_filename = os.path.join(configs.model_path, 'pretrained', 'fpn_resnet_18_epoch_300.pth')
        configs.pretrained_path = 'tools/objdet_models/resnet/pretrained/fpn_resnet_18_epoch_300.pth'
        configs.arch = 'fpn_resnet_18'
        configs.saved_fn = 'fpn_resnet_18'
        configs.batch_size = 1
        configs.num_samples = None
        configs.min_iou = 0.5  # minimum intersection over union for a valid detection
        configs.peak_thresh = 0.2
        configs.conf_thresh = 0.5
        configs.input_size = (608, 608)
        configs.hm_size = (152, 152)  # size of heatmap
        configs.down_ratio = 4  # down-sampling factor
        configs.max_objects = 50  # maximum number of objects per image
        configs.imagenet_pretrained = False  # use imagenet pre-trained weights
        configs.head_conv = 64  # number of channels in the head convolution
        configs.num_classes = 3  # number of classes (pedestrian, car, cyclist
        configs.num_center_offset = 2  # number of center offset coordinates
        configs.num_z  = 1  # number of z-coordinates
        configs.num_dim = 3  # number of dimensions (width, height, length)
        configs.num_direction = 2  # number of direction classes (left, right)
        configs.heads = {'hm_cen': configs.num_classes, 'cen_offset': configs.num_center_offset, 
                        'direction': configs.num_direction, 'z_coor': configs.num_z,'dim': configs.num_dim}
        configs.num_input_features = 4
        configs.save_test_output = False
        configs.no_cuda = False
        configs.gpu_idx = 0
        configs.output_format = 'image'
        configs.output_video_fn = 'out_fpn_resnet'
        configs.distributed = False
        configs.output_width= 608
        configs.num_samples = None
        configs.num_workers = 1
        configs.pin_memory = True
        configs.distributed = False
        print("student task ID_S3_EX1-3")

        #######
        ####### ID_S3_EX1-3 END #######     

    else:
        raise ValueError("Error: Invalid model name")

    # GPU vs. CPU
    configs.no_cuda = False # if true, cuda is not used
    configs.gpu_idx = 0  # GPU index to use.
    configs.device = torch.device('cpu' if configs.no_cuda else 'cuda:{}'.format(configs.gpu_idx))

    return configs


# load all object-detection parameters into an edict
def load_configs(model_name='fpn_resnet', configs=None):

    # init config file, if none has been passed
    if configs==None:
        configs = edict()    

    # birds-eye view (bev) parameters
    configs.lim_x = [0, 50] # detection range in m
    configs.lim_y = [-25, 25]
    configs.lim_z = [-1, 3]
    configs.lim_r = [0, 1.0] # reflected lidar intensity
    configs.bev_width = 608  # pixel resolution of bev image
    configs.bev_height = 608 

    # add model-dependent parameters
    configs = load_configs_model(model_name, configs)

    # visualization parameters
    configs.output_width = 608 # width of result image (height may vary)
    configs.obj_colors = [[0, 255, 255], [0, 0, 255], [255, 0, 0]] # 'Pedestrian': 0, 'Car': 1, 'Cyclist': 2

    return configs


# create model according to selected model type
def create_model(configs):

    # check for availability of model file
    assert os.path.isfile(configs.pretrained_filename), "No file at {}".format(configs.pretrained_filename)

    # create model depending on architecture name
    if (configs.arch == 'darknet') and (configs.cfgfile is not None):
        print('using darknet')
        model = darknet(cfgfile=configs.cfgfile, use_giou_loss=configs.use_giou_loss)    
    
    elif 'fpn_resnet' in configs.arch:
        print('using ResNet architecture with feature pyramid')
        
        ####### ID_S3_EX1-4 START #######     
        #######
        num_layers = 18
        model = fpn_resnet.get_pose_net(num_layers = num_layers, heads = configs.heads, 
                                        head_conv= configs.head_conv, 
                                        imagenet_pretrained = configs.imagenet_pretrained)
        print("student task ID_S3_EX1-4")

        #######
        ####### ID_S3_EX1-4 END #######     
    
    else:
        assert False, 'Undefined model backbone'

    # load model weights
    model.load_state_dict(torch.load(configs.pretrained_filename, map_location='cpu'))
    print('Loaded weights from {}\n'.format(configs.pretrained_filename))

    # set model to evaluation state
    configs.device = torch.device('cpu' if configs.no_cuda else 'cuda:{}'.format(configs.gpu_idx))
    model = model.to(device=configs.device)  # load model to either cpu or gpu
    model.eval()          

    return model


# detect trained objects in birds-eye view
def detect_objects(input_bev_maps, model, configs):

    # deactivate autograd engine during test to reduce memory usage and speed up computations
    with torch.no_grad():  

        # perform inference
        outputs = model(input_bev_maps)

        # decode model output into target object format
        if 'darknet' in configs.arch:

            # perform post-processing
            output_post = post_processing_v2(outputs, conf_thresh=configs.conf_thresh, nms_thresh=configs.nms_thresh) 
            detections = []
            for sample_i in range(len(output_post)):
                if output_post[sample_i] is None:
                    continue
                detection = output_post[sample_i]
                for obj in detection:
                    x, y, w, l, im, re, _, _, _ = obj
                    # print(f"DEBUG: Detections fropm x={x:.2f}, y={y:.2f}, w={w:.2f}, l={l:.2f}, im={im:.2f}, re={re:.2f}")
                    yaw = np.arctan2(im, re)
                    detections.append([1, x, y, 0.0, 1.50, w, l, yaw])    

        elif 'fpn_resnet' in configs.arch:
            # decode output and perform post-processing
            
            ####### ID_S3_EX1-5 START #######     
            #######
            print("student task ID_S3_EX1-5")
            outputs['hm_cen'] = torch.sigmoid(outputs['hm_cen'])
            outputs['cen_offset'] = torch.sigmoid(outputs['cen_offset'])

            detections = decode(
                outputs['hm_cen'], 
                outputs['cen_offset'],
                outputs['direction'],
                outputs['z_coor'], 
                outputs['dim'],
                K=40
            )
            detections = detections.cpu().numpy().astype(np.float32)

            detections = post_processing(
                    detections, 
                    configs
                )
            detections = detections[0][1]
            # print(detections)
            # final_detections = []
            # for detection in detections[0]:  # batch size = 1
            #     for obj in detection:
            #         cls_id, x, y, z, h, w, l, yaw = obj[:8]
            #         final_detections.append([cls_id, x, y, z, h, w, l, yaw])

            # detections = final_detections

            #######
            ####### ID_S3_EX1-5 END #######     

            

    ####### ID_S3_EX2 START #######     
    #######
    # Extract 3d bounding boxes from model response
    print("student task ID_S3_EX2")
    objects = [] 

    if len(detections) > 0:
        for obj in detections:
            if configs.arch == 'darknet':
                # darknet model output generated raw pixel data in width and length so we need to scale it up
                cls_id, x_img, y_img, z_norm, h, w, l, yaw = obj
                bev_x_discret = (configs.lim_x[1] - configs.lim_x[0]) / configs.bev_height
                bev_y_discret = (configs.lim_y[1] - configs.lim_y[0]) / configs.bev_width
                x_world = y_img * bev_x_discret + configs.lim_x[0]
                y_world = x_img * bev_y_discret + configs.lim_y[0]
                z_world = 0
                w_world = w * bev_x_discret
                l_world = l * bev_y_discret

            elif configs.arch == 'fpn_resnet_18':
                # For ResNet output: The model output is different so need different processing for width and length
                cls_id, x_img, y_img, z_norm, h, w, l, yaw = obj
                bev_x_discret = (configs.lim_x[1] - configs.lim_x[0]) / configs.bev_height
                bev_y_discret = (configs.lim_y[1] - configs.lim_y[0]) / configs.bev_width
                x_world = y_img * bev_x_discret + configs.lim_x[0]
                y_world = x_img * bev_y_discret + configs.lim_y[0]
                z_world = z_norm * (configs.lim_z[1] - configs.lim_z[0]) + configs.lim_z[0]
                w_world = w
                l_world = l

            objects.append([cls_id, x_world, y_world, z_world, h, w_world, l_world, yaw])
            
    ###### ID_S3_EX2 END #######   

    return objects 

