import os
import sys
import numpy as np

from scipy.io import wavfile
from time import *

import torch
import utils
from models import SynthesizerTrn


def save_wav(wav, path, rate):
    wav *= 32767 / max(0.01, np.max(np.abs(wav))) * 0.6
    wavfile.write(path, rate, wav.astype(np.int16))

# define model and load checkpoint
hps = utils.get_hparams_from_file("./configs/singing_base.json")

net_g = SynthesizerTrn(
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    **hps.model).cuda()

_ = utils.load_checkpoint("./logs/singing_base/G_270000.pth", net_g, None)
net_g.eval()
# net_g.remove_weight_norm()

# check directory existence
if not os.path.exists("./singing_out"):
    os.makedirs("./singing_out")

idxs = ["2001000001", "2001000002", "2001000003", "2001000004", "2001000005", "2001000006", "2051001912", "2051001913", "2051001914", "2051001915", "2051001916", "2051001917"]
for idx in idxs:
    text_norm = np.load(f"../VISinger_data/label_vits/{idx}_label.npy")
    text_tone = np.load(f"../VISinger_data/label_vits/{idx}_pitch.npy")
    input_f0 = torch.load(f"../VISinger_data/wav_dump_16k/{idx}_bits16.f0.pt")
    input_ids = torch.LongTensor(text_norm)
    tune_ids = torch.LongTensor(text_tone)
    len_text = input_ids.size()[0]
    len_tone = tune_ids.size()[0]
    len_spec = input_f0.size()[-1]
    assert len_text == len_tone
    if (len_text != len_spec):
        len_min = min(len_text, len_spec)
        input_ids = input_ids[:len_min]
        tune_ids = tune_ids[:len_min]
        input_f0 = input_f0[:len_min]

    begin_time = time()
    with torch.no_grad():
        x_tst = input_ids.cuda().unsqueeze(0)
        x_tst_lengths = torch.LongTensor([input_ids.size(0)]).cuda()
        t_tst = tune_ids.cuda().unsqueeze(0)
        t_tst_lengths = torch.LongTensor([tune_ids.size(0)]).cuda()
        f0_tst = input_f0.cuda().unsqueeze(0)
        audio = net_g.infer(x_tst, x_tst_lengths, t_tst, t_tst_lengths, f0_tst, t_tst_lengths, noise_scale=0, noise_scale_w=0, length_scale=1)[0][0,0].data.cpu().float().numpy()
    end_time = time()
    run_time = end_time - begin_time
    print('Syth Time (Seconds):', run_time)
    data_len = len(audio) / 16000
    print('Wave Time (Seconds):', data_len)
    print('Real time Rate (%):', run_time/data_len)
    save_wav(audio, f"./singing_out/singing_{idx}.wav", hps.data.sampling_rate)

# can be deleted
os.system("chmod 777 ./singing_out -R")
