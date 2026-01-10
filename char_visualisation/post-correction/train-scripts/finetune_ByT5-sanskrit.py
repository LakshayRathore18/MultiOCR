from transformers import HfArgumentParser, TensorFlowBenchmark, TensorFlowBenchmarkArguments
import pandas as pd
from transformers import T5ForConditionalGeneration, AutoTokenizer
from transformers import TrainingArguments
from torch.utils.data import Dataset, DataLoader
from transformers import Trainer
from transformers import EarlyStoppingCallback
from transformers.optimization import Adafactor, AdafactorSchedule
import torch
import os
# torch.cuda.empty_cache()


import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune the ByT5 model.")
    parser.add_argument('--experiment', required=True, help='Experiment ID')
    parser.add_argument('--fold', type=int, required=True, help='Fold number')
    # Add more arguments if needed
    return parser.parse_args()

def main():
  _args = parse_args()
  #######
  experiment = _args.experiment
  fold = _args.fold
  #######


  device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
  print(f"Using device: {device}")
  # torch.cuda.set_per_process_memory_fraction(0.5, device=0) 


  finetune_iter = 1500 
  tokenizer_path = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/downloaded_model/models--byt5-sanskrit'
  #model_path = '/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/downloaded_model/checkpoint-1100-big'
  model_path = tokenizer_path


  train_df = pd.read_csv(f"/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/data/experiment_{experiment}/train_fold_{fold}.csv",delimiter=';')
  eval_df = pd.read_csv(f"/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/data/experiment_{experiment}/val_fold_{fold}.csv",delimiter=';')
  test_df = pd.read_csv(f"/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/data/experiment_{experiment}/test_fold_{fold}.csv",delimiter=';')

  model_save_directory = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/model_checkpoints/experiment_{experiment}/{fold}'

  if not os.path.exists(model_save_directory):
      os.makedirs(model_save_directory)
      print(f"Directory created: {model_save_directory}")
  else:
      print(f"Directory already exists: {model_save_directory}")



  args_dict = {
      # "model_name_or_path": 'google/byt5-small',
      # "max_len": 4096,
      "output_dir": model_save_directory,
      "overwrite_output_dir": True,
      "per_device_train_batch_size": 2,
      "per_device_eval_batch_size": 1,
      "gradient_accumulation_steps": 1,
      #"learning_rate": 5e-5, #5e-4
      #"warmup_steps": 50,
      "logging_steps": 100,
      "evaluation_strategy": "steps",
      "eval_steps": 100,
      "num_train_epochs": 4,
      "do_train": True,
      "do_eval": True,
      "fp16": False,
      # "use_cache": False,
      "max_steps": finetune_iter,
      'save_steps':100,
      'save_strategy':'steps',
      'load_best_model_at_end': True,
      'metric_for_best_model':'eval_loss',
      'greater_is_better':False,
      'save_total_limit' : 3
  }
  parser = HfArgumentParser(
          (TrainingArguments))
  training_args = parser.parse_dict(args_dict)
  # set_seed(training_args.seed)
  args = training_args[0]

  # Load pretrained model and tokenizer
  tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
  model = T5ForConditionalGeneration.from_pretrained(model_path).to(device)
  #instead of T5ForConditionalGeneration, use T5ForMaskedLM
  #model = T5ForMaskedLM.from_pretrained(model_path).to(device)

  # overwriting the default max_length of 20 
  # tokenizer.model_max_length=4096
  # model.config.max_length=4096



  class GPReviewDataset(Dataset):
    def __init__(self, Text, Label):
      self.Text = Text
      self.Label = Label
      # self.tokenizer = tokenizer
      # self.max_len = max_len
    def __len__(self):
      return len(self.Text)
    def __getitem__(self, item):
      Text = str(self.Text[item])
      Label = self.Label[item]
      inputs = tokenizer(Text, padding="max_length", truncation=True, max_length=512)
      outputs = tokenizer(Label, padding="max_length", truncation=True, max_length=512)
      return {
        "input_ids":inputs.input_ids,
        "attention_mask" : inputs.attention_mask,
        "labels" : outputs.input_ids,
        "decoder_attention_mask" : outputs.attention_mask,
        # "labels" : lbz
      }

  ds_train = GPReviewDataset(
    Text=train_df.input_text.to_numpy(),
    Label=train_df.target_text.to_numpy()
    # tokenizer=tokenizer,
    # max_len=max_len
  )


  ds_test = GPReviewDataset(
    Text=eval_df.input_text.to_numpy(),
    Label=eval_df.target_text.to_numpy()
    # tokenizer=tokenizer,
    # max_len=max_len
  )


  train_dataset = ds_train
  valid_dataset = ds_test

    # replace AdamW with Adafactor
  optimizer = Adafactor(
      model.parameters(),
      lr=None,
      #eps=(1e-30, 1e-3),
      #clip_threshold=1.0,
      #decay_rate=-0.8,
      #beta1=None,
      #weight_decay=0.0,
      relative_step=True,
      scale_parameter=True,
      warmup_init=True,
  )
  lr_scheduler = AdafactorSchedule(optimizer)
  trainer = Trainer(
      model=model,
      args=args,
      train_dataset=train_dataset,
      eval_dataset=valid_dataset,
      optimizers=(optimizer,lr_scheduler)
      # callbacks = [EarlyStoppingCallback(early_stopping_patience=10)]
      # compute_metrics=compute_metrics
  )

  trainer.train()

  # Write the best model checkpoint path to a file
  with open(model_save_directory+'/best_model_checkpoint.txt', 'w') as f:
      f.write(trainer.state.best_model_checkpoint)



if __name__ == "__main__":
    main()