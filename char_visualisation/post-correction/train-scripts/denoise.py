"""Script to denoise first pass OCR outputs using a small amount of corrected data.

The small amount of manually corrected data is used to create probabilistic "denoising rules".
The rules are then applied to the input first pass files to automatically create "denoised outputs"

The denoised outputs are subsequently used to pretrain the post-correction model.

Usage:
python denoise.py --train_src1 data/big_src.txt --train_tgt data/big_tgt.txt
Copyright (c) 2021, Shruti Rijhwani
All rights reserved.

This source code is licensed under the BSD-style license found in the
LICENSE file in the root directory of this source tree. 
"""




import matplotlib.pyplot as plt
import argparse
import glob
import random
import Levenshtein
from collections import defaultdict
import json
from aksharamukha import transliterate
import unicodedata
import pandas as pd
import re
import os

convert_to_SLP = True


def extract_experiment_and_fold(path):
    # Use regex to extract experiment and fold numbers from the file path
    match = re.search(r'experiment_([\w-]+)/(train_fold|test_fold)_(\d+)', path)
    if match:
        experiment_number = match.group(1)
        fold_number = match.group(3)
        return experiment_number, fold_number
    else:
        raise ValueError("Path does not contain experiment and fold numbers")

class Denoiser(object):
    def preprocess(self, text):
        preprocessed = " ".join(text.strip().split())
        return preprocessed

    def count_chars(self, predicted_text, char_counts):
        for c in predicted_text:
            char_counts[c] += 1
            char_counts["total"] += 1

    def error_distribution(self, src, tgt, errors):
        edits = Levenshtein.editops(src, tgt)
        for edit in edits:
            if edit[0] == "replace":
                errors[("replace", src[edit[1]], tgt[edit[2]])] += 1
            elif edit[0] == "delete":
                errors[("delete", src[edit[1]])] += 1
            elif edit[0] == "insert":
                errors[("insert", tgt[edit[2]])] += 1
            else:
                print(edit)

    def create_rules(self, filepath,train):
        df = pd.read_csv(filepath, delimiter=';',encoding="utf8")
    
        # Extract the columns
        if train:
            src_lines = df['input_text'].tolist()
            tgt_lines = df['target_text'].tolist()
        else:
            src_lines = df['input_text'].tolist()
            tgt_lines = df['predicted_text'].tolist()
        
        
        # Assert that both columns have the same length
        assert len(src_lines) == len(tgt_lines)

        errors = defaultdict(lambda: 0)
        char_counts = defaultdict(lambda: 0)

        for src_line, tgt_line in zip(src_lines, tgt_lines):
            if convert_to_SLP:
                src_line = transliterate.process('IAST', 'Devanagari', src_line)
                tgt_line = transliterate.process('IAST', 'Devanagari', tgt_line)

            if (not src_line.strip()) or (not tgt_line.strip()):
                continue

            self.error_distribution(
                self.preprocess(src_line), self.preprocess(tgt_line), errors
            )
            self.count_chars(self.preprocess(src_line), char_counts)

        rules = {}
        for k, v in errors.items():
            if k[0] == "replace":
                rules[(k[0], k[1], k[2])] = v / char_counts[k[1]]
            elif k[0] == "delete":
                rules[(k[0], k[1], "")] = v / char_counts[k[1]]
            elif k[0] == "insert":
                rules[(k[0], k[1], "")] = v / char_counts["total"]

        errors_ = {str(key): value for key, value in errors.items()}
        char_counts_ = {str(key): value for key, value in char_counts.items()}
        return rules,(errors_ ,char_counts_)

    def denoise_file(self, rules, input_file, output_file):
        with open(input_file, "r", encoding="utf8") as f, open(
            output_file, "w", encoding="utf8"
        ) as out:
            for line in f:
                line = line.strip()
                if convert_to_SLP:
                    line = transliterate.process('IAST', 'Devanagari', line)
                for (rule_type, c_1, c_2), prob in rules.items():
                    if rule_type == "delete":
                        rand_delete = (
                            lambda c: "" if random.random() < prob and c == c_1 else c
                        )
                        line = "".join([rand_delete(c) for c in line])
                    elif rule_type == "replace":
                        rand_replace = (
                            lambda c: c_2 if random.random() < prob and c == c_1 else c
                        )
                        line = "".join([rand_replace(c) for c in line])
                    elif rule_type == "insert":
                        line = line + " "
                        rand_insert = (
                            lambda c: "{}{}".format(c_1, c)
                            if random.random() < prob
                            else c
                        )
                        line = "".join([rand_insert(c) for c in line])
                out.write(line.strip() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv_file",
        help="path to the csv file",
    )
    parser.add_argument(
        "--train",
        action='store_true',
        help="Do we want the error rates for the training data or the test data?",
    )
    # parser.add_argument(
    #     "--input",
    #     help="Input file to denoise. Typically these are the uncorrected src1 for pretraining.",
    # )
    # parser.add_argument("--output", help="Output filename.")
    args = parser.parse_args()

    denoiser = Denoiser()
    rules,cc = denoiser.create_rules(filepath=args.csv_file, train=args.train)
    sorted_data = dict(sorted(cc[0].items(), key=lambda item: item[1], reverse=True))


    experiment_number, fold_number = extract_experiment_and_fold(args.csv_file)
    path = f'/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/experiment_{experiment_number}/test_fold_{fold_number}'
    if args.train:
        output_file = os.path.join(path, 'error_counts_train.json')
    else:
        output_file = os.path.join(path, 'error_counts_test.json')

    # Save the dictionary to a JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=4)

    #denoiser.denoise_file(rules=rules, input_file=args.input, output_file=args.output)