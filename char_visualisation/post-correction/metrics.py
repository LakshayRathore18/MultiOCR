import pandas as pd
import editdistance as ed
from collections import defaultdict
import argparse
import sys
import os
import matplotlib.pyplot as plt


def calculate_metrics(predicted_text, transcript):
    cer = ed.eval(predicted_text, transcript) / max(len(predicted_text), len(transcript))
    pred_spl = predicted_text.split()
    transcript_spl = transcript.split()
    wer = ed.eval(pred_spl, transcript_spl) /  max(len(pred_spl), len(transcript_spl))
    return cer, wer


def rem(s):
  # print(s)
  return s.replace("\n",'')


def get_metric(folder_path, df_output):
  #df_output = pd.read_csv(filename, sep=';')

  # df_output['input_text'] = df_output['input_text'].apply(lambda x: rem(x))
  # df_output['target_text'] = df_output['target_text'].apply(lambda x: rem(x))
  # df_output['predicted_text'] = df_output['predicted_text'].apply(lambda x: rem(x))

  # df_output['input_text'] = df_output['input_text'].apply(lambda x:x.rstrip().lstrip())
  # df_output['target_text'] = df_output['target_text'].apply(lambda x:x.rstrip().lstrip())
  # df_output['predicted_text'] = df_output['predicted_text'].apply(lambda x:x.rstrip().lstrip())

  for index, row in df_output.iterrows():
    ocr_output = row['input_text']
    ref = row['target_text']
    nlp_output = row['predicted_text']
    
    pre_cer,pre_wer = calculate_metrics(ocr_output,ref)
    post_cer,post_wer = calculate_metrics(nlp_output,ref)
    
    df_output.loc[index, 'pre_cer'] = round(pre_cer,2) # Round value to 2 decimal places
    df_output.loc[index, 'pre_wer'] = round(pre_wer,2)

    df_output.loc[index, 'post_cer'] = round(post_cer,2) # Round value to 2 decimal places
    df_output.loc[index, 'post_wer'] = round(post_wer,2)


  df_output['difference'] = df_output['post_cer'] - df_output['pre_cer']
  sorted_df = df_output#.sort_values(by='difference')

  columns_to_save = ['difference', 'pre_cer', 'post_cer', 'input_text', 'target_text','predicted_text','path']

  sorted_df[columns_to_save].to_csv(folder_path+f'/analysis.csv',sep=';', index=False)

  
  #image
  plt.hist(sorted_df['difference'], bins=20, edgecolor='black')  # Adjust bins and edgecolor as needed
  plt.xlabel('Values')  # Set xlabel
  plt.ylabel('Frequency')  # Set ylabel
  plt.title('Negative is good')  # Set title
  plt.savefig(folder_path+'/histogram.png')


  # Overall performances
  pre_mean_cer = df_output['pre_cer'].mean()
  pre_mean_wer = df_output['pre_wer'].mean()

  post_mean_cer = df_output['post_cer'].mean()
  post_mean_wer = df_output['post_wer'].mean()


  print(f'Pre Mean CER = {pre_mean_cer}%, Pre Mean WER = {pre_mean_wer}%')
  print(f'Post Mean CER = {post_mean_cer}%, Post Mean WER = {post_mean_wer}%')
  
  return pre_mean_cer, post_mean_cer

if __name__=="__main__":

  fname = sys.argv[1]
  cer, wer = get_metric(sys.argv[1])

