# Set the experiment number
EXPERIMENT=messy_transferCheck_1x

# Loop over folds from 1 to 3
for FOLD in {1..1}
do
    echo "Processing fold $FOLD..."

    /home/ocr_proj/.conda/envs/ByT5/bin/python /home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/train-scripts/transfer_inference-byt5-sanskrit.py --experiment $EXPERIMENT --fold $FOLD

    # getting the error counts..

    TEST_PATH=/home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/outputs/experiment_$EXPERIMENT/test_fold_$FOLD/analysis.csv
    /home/ocr_proj/.conda/envs/ByT5/bin/python /home/ocr_proj/OCR/post_correction/pe-ocr-sanskrit/train-scripts/denoise.py --csv_file $TEST_PATH

    echo "Completed fold $FOLD"
done




