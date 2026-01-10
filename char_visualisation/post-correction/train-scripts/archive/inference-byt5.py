from transformers import HfArgumentParser, TensorFlowBenchmark, TensorFlowBenchmarkArguments
import pandas as pd
from transformers import MBartForConditionalGeneration, MBart50TokenizerFast
from transformers import TrainingArguments
from torch.utils.data import Dataset, DataLoader
from transformers import T5ForConditionalGeneration, AutoTokenizer
from transformers import Trainer
from transformers import pipeline
from tqdm import tqdm
import time
import glob
import torch

import sys
sys.path.append("/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit")
from metrics import get_metric
device = torch.device('cuda')


load_checkpoint_iter = 1000
finetune_iter = 400
tokenizer_path = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/tokenizer_checkpoints'

tokenizer = AutoTokenizer.from_pretrained(tokenizer_path,max_length=512
)

# test_df = pd.read_csv("final_trans_data_OCR/test.csv")
test_df = pd.read_csv("/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/data/test_finetune.csv", sep=';') 

print('Test csv read')

def store_file(fullpath, checkpoint):
    ocr_pipeline = pipeline(
        'text2text-generation',
        model = fullpath,
    #    model="byt5-base-slp-ocr-correction/checkpoint-100000",
        # model="model_checkpoints/checkpoint-" + str(checkpoint),
        tokenizer=tokenizer,
        device=device)

    print('Model Loaded')
    start = time.time()
    # print('Time is ', start)
    results=  [] 
    data = list(test_df.input_text.values)

    results = ocr_pipeline(data)
    print('Total time taken to processis ', time.time()-start)
    pred_resultz = []
    for i in tqdm(list(range(len(results)))):
        for k,e in results[i].items():
            pred_resultz.append(e)

    res = pd.DataFrame(zip(test_df.input_text.values,test_df.target_text.values,pred_resultz),columns = ['input_text','target_text','predicted_text'])

    tgt_filename = "/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/external_ByT5_predictions_" + str(checkpoint) + ".csv"

    res.to_csv(tgt_filename,index = False,sep=';')
    return tgt_filename


if __name__ == '__main__':
    # dirs =  glob.glob('model_checkpoints/checkpoint-*')
    
    # for dirname in dirs:
        # ckpoint = str(dirname[-5:])
       
    #     tgt_filename = store_file(dirname, ckpoint)
    #     cer, wer = get_metric(tgt_filename)
    #     print('For checkpoint ', ckpoint , f', Mean CER = {cer}%, Mean WER = {wer}%')
    
    dirs =  f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/model_checkpoints/checkpoint-{load_checkpoint_iter+finetune_iter}'
    ckpoint = str(dirs[-5:])
    tgt_filename = store_file(dirs, ckpoint)
    cer, wer = get_metric(tgt_filename)
    print('For checkpoint ', ckpoint , f', Mean CER = {cer}%, Mean WER = {wer}%')
    