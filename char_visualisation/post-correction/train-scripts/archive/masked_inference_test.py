import argparse
import pandas as pd
from transformers import AutoTokenizer, pipeline, AutoModelForSeq2SeqLM
import torch
import os
import time
from tqdm import tqdm
import editdistance as ed

# TODO
# simplify the code
# make sure I'm not missing any config details.
# compare the performance of the base model and with the fine-tuned model

import sys
sys.path.append("/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit")
from metrics import get_metric
device = torch.device('cuda')

def get_edit_distance(predicted_text, transcript):
    cer = ed.eval(predicted_text, transcript) / max(len(predicted_text), len(transcript))
    return cer


# Function to store file results
def generate_text(pretrained_model_dir, tokenizer, test_df):
    model = AutoModelForSeq2SeqLM.from_pretrained(pretrained_model_dir)
    
    for i in range(0,6):
        ocr_text = list(test_df.input_text.values)[0][i:-i]
        target_text = list(test_df.target_text.values)[0][i:-i]

        output_ids = model.generate(torch.tensor([tokenizer(ocr_text).input_ids]),max_length=100, num_beams=3, eos_token_id=1, pad_token_id=0,decoder_start_token_id=0)[0].tolist()
        output_text = tokenizer.batch_decode(output_ids)
        # print edit distance between target_text and output_text
        print(ocr_text)
        print(''.join(output_text))
        print(target_text)
        print(get_edit_distance( output_text,target_text))      




        
           




    # device = torch.device('cuda')
    # ocr_pipeline = pipeline(
    #     'text2text-generation',
    #     model=pretrained_model_dir,
    #     tokenizer=tokenizer,
    #     device=device,
    #     num_beams=3,
    # )

    # print('Model Loaded')
    # start = time.time()
    # results = [] 
    # data = list(test_df.input_text.values)

    # results = ocr_pipeline(data)
    # #instead of text2text-generation, use MaskGenerationPipeline
    # #       



    # print('Total time taken to process is ', time.time() - start)
    # pred_resultz = []
    # for i in tqdm(list(range(len(results)))):
    #     for k, e in results[i].items():
    #         pred_resultz.append(e)

    # res = pd.DataFrame(zip(test_df.input_text.values, test_df.target_text.values, pred_resultz, test_df.path), columns=['input_text', 'target_text', 'predicted_text', 'path'])

    # return res

def main():
    # Parse arguments
    #args = parse_args()
    
    # Define paths using arguments
    # experiment = args.experiment
    # fold = args.fold
    experiment = 'big_7pagetrained_1x'
    fold = 1

    data_path = f"/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/data/experiment_{experiment}/test_fold_{fold}.csv"
    tokenizer_path = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/downloaded_model/models--byt5-sanskrit'
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, max_length=512)
    pretrained_model_dir = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/downloaded_model/models--byt5-sanskrit'



    # Ensure the results directory exists
    dir_path = os.path.dirname(data_path)
    experiment_folder = os.path.basename(dir_path)
    folder_name = os.path.splitext(os.path.basename(data_path))[0]
    results_folder_path = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/MASK_{experiment_folder}/{folder_name}'
    if not os.path.exists(results_folder_path):
        os.makedirs(results_folder_path)
        print(f"Directory created: {results_folder_path}")
    else:
        print(f"Directory already exists: {results_folder_path}")



    # Read the test CSV file
    test_df = pd.read_csv(data_path, sep=';')
    print('Test csv read')
    results_csv = generate_text(pretrained_model_dir, tokenizer, test_df)
    
    # # Calculate and print metrics (assuming get_metric is defined elsewhere)
    # pre_cer, post_cer = get_metric(results_folder_path, results_csv)
    # results_file = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/{experiment_folder}/results.txt'
    # with open(results_file, 'a') as file:
    #     file.write(f'Pre CER - Post CER : {pre_cer-post_cer}\n')

    # print('For checkpoint ', ckpoint , f', Mean CER = {cer}%, Mean WER = {wer}%')

if __name__ == '__main__':
    main()
