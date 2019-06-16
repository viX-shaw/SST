from tracker import SSTTracker, TrackerConfig, Track
import cv2
from data.ua_detection_data_reader import UADetectionDataReader
import numpy as np
from config.config import config
from utils.timer import Timer
import argparse
import os
from tools import preprocessing

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description='Single Shot Tracker Test')
parser.add_argument('--version', default='v1', help='current version')
parser.add_argument('--ua_image_root', default=config['ua_image_root'], help='Image Root')
parser.add_argument('--ua_detection_root', default=config['ua_detection_root'], help='Detection Root')
parser.add_argument('--ua_ignore_root', default=config['ua_ignore_root'], help='Ignore folder Root')
parser.add_argument('--save_folder', default=config['save_folder'], help='save file folder Root')
parser.add_argument('--show_image', type=str2bool, default=False, help='show image if true, or hidden')
parser.add_argument('--save_video', type=str2bool, default=True, help='save video if true')
parser.add_argument('--use_ignore', type=str2bool, default=False, help='use ignore or not')
parser.add_argument('--detection_threshold', default=0.3, help='the threshold of detection')
parser.add_argument('--nms_max_overlap', default=0.3, help='maximum overlap allowd b/w detections')

args = parser.parse_args()

def test(choice=None, sequence_list=None):
    image_root = args.ua_image_root
    detection_root = args.ua_detection_root
    ignore_root = args.ua_ignore_root
    save_folder = args.save_folder
    use_ignore = args.use_ignore 

    if not os.path.exists(image_root) or not os.path.exists(detection_root) or not os.path.exists(ignore_root):
        raise FileNotFoundError('Pls check the file of parameters')

    print(isinstance(args.save_video, bool), args.save_video)
    print('''
    ==============================
    =     Start Reading Files    =
    ==============================
    ''')

    if not sequence_list is None:
        sequences = np.loadtxt(sequence_list, dtype='str')
    else:
        sequences = os.listdir(image_root)
    
    sequences_basename = [os.path.basename(s) for s in sequences]
    # print(sequences_basename)
    # validation
    for seq in sequences:
        if not os.path.exists(os.path.join(image_root, seq)):
            raise FileNotFoundError()

    all_image_folders = sorted(
        [os.path.join(image_root, d) for d in sequences]
    )
    # print(all_image_folders)

    # all_detection_files = [os.path.join(detection_root, f+'_Det_'+config['detector_name']+'.txt') for f in sequences_basename]
    all_detection_files = [os.path.join(detection_root, f) for f in os.listdir(detection_root)]
    # all_ignore_files = [os.path.join(ignore_root, f+'_IgR.txt') for f in sequences_basename]
    all_ignore_files = [os.path.join(ignore_root, f) for f in os.listdir(ignore_root)]

    # all_detection_files = sorted(
    #     [os.path.join(detection_root, f) for f in os.listdir(detection_root) if 'MVI_' in f and os.path.basename(f) in sequences_basename]
    # )
    # all_ignore_files = sorted(
    #     [os.path.join(ignore_root, f) for f in os.listdir(ignore_root) if os.path.basename(f)[:-8] in sequences_basename]
    # )
    # print(all_ignore_files)

    ignore_file_base_name = [os.path.basename(f)[:-8] for f in all_ignore_files]
    detection_file_base_name = [os.path.basename(f)[:9] for f in all_detection_files]

    choice_str = ''
    if not choice is None:
        choice_str =  TrackerConfig.get_configure_str(choice)
        TrackerConfig.set_configure(c)
        save_folder = os.path.join(args.save_folder, choice_str)
        if not os.path.exists(save_folder):
            os.mkdir(save_folder)

    saved_file_name_format = os.path.join(save_folder, '{}.txt')
    saved_video_name_format = os.path.join(save_folder, '{}.avi')

    for i, image_fol in enumerate(all_image_folders):
        # image_folder_base_name = os.path.basename(image_folder)
        # i = ignore_file_base_name.index(image_folder_base_name)
        # ignore_file = all_ignore_files[i]

        # j = detection_file_base_name.index(image_folder_base_name)
        # detection_file = all_detection_files[j]

        image_folder = image_fol+"/img1"
        detection_file = image_fol+"/det/det.txt"
        ignore_file = "." 

        saved_file_name = saved_file_name_format.format(i)
        saved_video_name = saved_video_name_format.format(i)
        vw = None
        if not os.path.exists(image_folder) or not os.path.exists(detection_file) or not os.path.exists(ignore_file):
            continue

        print('processing ', image_folder, '>>>>>>>>>>>>>>>>>>')

        tracker = SSTTracker()
        reader = UADetectionDataReader(image_folder, detection_file, ignore_file if use_ignore else None,
                                       args.detection_threshold)
        # break
        result = list()
        result_str = saved_file_name
        timer = Timer()
        for i, item in enumerate(reader):
            # print("length", reader.length)
            if item is None:
                # print("No item found")
                continue

            img = item[0]
            det = item[1]


            if img is None or det is None or len(det) == 0:
                continue
            print(det)

            indices = preprocessing.non_max_suppression(det[:, [2,3,4,5]], args.nms_max_overlap)
            det = det[indices, :] 

            print(det)
            if len(det) > config['max_object']:
                det = det[:config['max_object'], :]

            h, w, _ = img.shape
            if vw is None and args.save_video:
                print("Creating videowiter")
                vw = cv2.VideoWriter(saved_video_name, cv2.VideoWriter_fourcc('M','J','P','G'), 10, (w, h))

            det[:, [2, 4]] /= float(w)
            det[:, [3, 5]] /= float(h)

            timer.tic()
            image_org = tracker.update(img, det[:, 2:6], args.show_image, i)
            # print("Image Update", image_org)
            timer.toc()
            if i % 20 == 0:
                print('{}:{}, {}, {}, {}\r'.format(saved_file_name, i, int(i * 100 / reader.length), choice_str, args.detection_threshold))

            if args.show_image and not image_org is None:
                cv2.imshow('res', image_org)
                cv2.waitKey(1)

            if args.save_video:
                # print("Adding frame to vid")
                if image_org is None:
                    vw.write(img)
                else:
                    vw.write(image_org)

            for t in tracker.tracks:
                n = t.nodes[-1]
                if t.age == 1:
                    b = n.get_box(tracker.frame_index-1, tracker.recorder)
                    result.append(
                        [i+1] + [t.id+1] + [b[0]*w, b[1]*h, b[2]*w, b[3]*h] + [-1, -1, -1, -1]
                    )
        # save data
        if len(result) > 0 :
            save_format = '%d %d %1.2f %1.2f %1.2f %1.2f %d %d %d %d'
        else:
            save_format = '%i'
        np.savetxt(saved_file_name, np.array(result).astype(int), fmt=save_format)
        np.savetxt(os.path.splitext(saved_file_name)[0]+'-speed.txt', np.array([timer.total_time]), fmt='%.3f')
        print(result_str)

    # print(timer.total_time)
    # print(timer.average_time)


if __name__ == '__main__':
    c = TrackerConfig.get_ua_choice()
    threshold = [0.3] #[i*0.1 for i in range(11)]
    save_folder = args.save_folder
    if not os.path.exists(args.save_folder):
        os.mkdir(args.save_folder)
    for t in threshold:
        args.detection_threshold = t
        args.save_folder = os.path.join(save_folder, '{0:0.1f}'.format(t))
        if not os.path.exists(args.save_folder):
            os.mkdir(args.save_folder)
        # test(c, './config/ua_experienced.txt')
        test(c)

    # for i in range(10):
    #     #     c = all_choices[-i]
    #     #
    #     #     choice_str = TrackerConfig.get_configure_str(c)
    #     #     TrackerConfig.set_configure(c)
    #     #     print('=============================={}.{}=============================='.format(i, choice_str))
    #     #     test(c)
