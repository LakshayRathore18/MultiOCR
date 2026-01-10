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
import os

import sys
sys.path.append("/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit")
from metrics import get_metric
device = torch.device('cuda')

#######
experiment = 0
fold = 2
best_model_number = 800
#######


data_path = f"/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/data/experiment_{experiment}/test_fold_{fold}.csv"
 #select model number with the best val accuracy
tokenizer_path = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/downloaded_model/models--byt5-sanskrit'
tokenizer = AutoTokenizer.from_pretrained(tokenizer_path,max_length=512)

# Extract the folder name from the data_path
dir_path = os.path.dirname(data_path)
# Get the last part of the directory path
experiment_folder = os.path.basename(dir_path)
folder_name = os.path.splitext(os.path.basename(data_path))[0] #start here!! 
results_folder_path = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/{experiment_folder}/{folder_name}'
if not os.path.exists(results_folder_path):
    os.makedirs(results_folder_path)
    print(f"Directory created: {results_folder_path}")
else:
    print(f"Directory already exists: {results_folder_path}")


# test_df = pd.read_csv("final_trans_data_OCR/test.csv")
test_df = pd.read_csv(data_path, sep=';') 
print('Test csv read')



def store_file(fullpath, checkpoint):
    ocr_pipeline = pipeline(
        'text2text-generation',
        model = fullpath,
    #    model="byt5-base-slp-ocr-correction/checkpoint-100000",
        # model="model_checkpoints/checkpoint-" + str(checkpoint),
        tokenizer=tokenizer,
        device=device,

        num_beams=3,
        #temperature=0.0,
        # num_beam_groups=3,
        # diversity_penalty=0.8,
        #bad_words_ids
        #
        )

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

    res = pd.DataFrame(zip(test_df.input_text.values,test_df.target_text.values,pred_resultz,test_df.path),columns = ['input_text','target_text','predicted_text','path'])

    

    #res.to_csv(tgt_filename,index = False,sep=';')

    return results_folder_path,checkpoint,res


if __name__ == '__main__':
    # dirs =  glob.glob('model_checkpoints/checkpoint-*')
    
    # for dirname in dirs:
        # ckpoint = str(dirname[-5:])
       
    #     tgt_filename = store_file(dirname, ckpoint)
    #     cer, wer = get_metric(tgt_filename)
    #     print('For checkpoint ', ckpoint , f', Mean CER = {cer}%, Mean WER = {wer}%')
    
    dirs =  f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/model_checkpoints/experiment_{experiment}/{fold}/checkpoint-{best_model_number}'
    ckpoint = str(best_model_number)
    results_folder_path,checkpoint,results_csv = store_file(dirs, ckpoint)
    cer, wer = get_metric(results_folder_path,checkpoint,results_csv)
    print('For checkpoint ', ckpoint , f', Mean CER = {cer}%, Mean WER = {wer}%')
    