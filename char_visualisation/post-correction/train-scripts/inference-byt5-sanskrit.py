import argparse
import pandas as pd
from transformers import AutoTokenizer, pipeline
import torch
import os
import time
from tqdm import tqdm

import sys
sys.path.append("/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit")
from metrics import get_metric
device = torch.device('cuda')

# Define the argument parser
def parse_args():
    parser = argparse.ArgumentParser(description="Run model evaluation and metrics calculation.")
    parser.add_argument('--experiment', required=True, help='Experiment ID')
    parser.add_argument('--fold', type=int, required=True, help='Fold number')
    return parser.parse_args()

# Function to store file results
def store_file(fullpath, tokenizer, test_df):
    device = torch.device('cuda')
    ocr_pipeline = pipeline(
        'text2text-generation',
        model=fullpath,
        tokenizer=tokenizer,
        device=device,
        num_beams=3,
    )

    print('Model Loaded')
    start = time.time()
    test_df = test_df.reset_index(drop=True)
    data = test_df['input_text'].tolist()
    #data = list(test_df.input_text.values)
    results = ocr_pipeline(data)
    #instead of text2text-generation, use MaskGenerationPipeline
    #       

    print('Total time taken to process is ', time.time() - start)
    
    pred_resultz = []
    for i in tqdm(list(range(len(results)))):
        for k, e in results[i].items():
            pred_resultz.append(str(e))

    # res = pd.DataFrame(zip(test_df.input_text.values, test_df.target_text.values, pred_resultz, test_df.path), columns=['input_text', 'target_text', 'predicted_text', 'path'], 
    #                    index=test_df.index)

    res = pd.DataFrame({
                'input_text': test_df.input_text.astype('U'),
                'target_text': test_df.target_text.astype('U'),
                'predicted_text': pred_resultz,  # Ensuring pred_resultz is converted to strings
                'path': test_df.path.astype('U')
            })
    
    assert all(res.index == test_df.index), "Order mismatch detected"

    return res

def main():
    # Parse arguments
    args = parse_args()
    
    # Define paths using arguments
    experiment = args.experiment
    fold = args.fold

    data_path = f"/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/data/experiment_{experiment}/test_fold_{fold}.csv"
    tokenizer_path = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/downloaded_model/models--byt5-sanskrit'
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, max_length=512)
    model_save_directory = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/model_checkpoints/experiment_{experiment}/{fold}'+'/best_model_checkpoint.txt'
    with open(model_save_directory, 'r') as file:
        pretrained_model_dir = file.read() # this is the path of the checkpoint which did the best on the evaluation data

    #pretrained_model_dir = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/downloaded_model/models--byt5-sanskrit'
    # Ensure the results directory exists
    dir_path = os.path.dirname(data_path)
    experiment_folder = os.path.basename(dir_path)
    folder_name = os.path.splitext(os.path.basename(data_path))[0]
    results_folder_path = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/{experiment_folder}/{folder_name}'
    if not os.path.exists(results_folder_path):
        os.makedirs(results_folder_path)
        print(f"Directory created: {results_folder_path}")
    else:
        print(f"Directory already exists: {results_folder_path}")

    # Read the test CSV file
    test_df = pd.read_csv(data_path, sep=';', encoding='utf-8',index_col=False)
    print('Test csv read')
    results_csv = store_file(pretrained_model_dir, tokenizer, test_df)
    
    # Calculate and print metrics (assuming get_metric is defined elsewhere)
    pre_cer, post_cer = get_metric(results_folder_path, results_csv)
    results_file = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/{experiment_folder}/results.txt'
    with open(results_file, 'a') as file:
        file.write(f'Pre CER - Post CER : {pre_cer-post_cer}\n')

    # print('For checkpoint ', ckpoint , f', Mean CER = {cer}%, Mean WER = {wer}%')

if __name__ == '__main__':
    main()
