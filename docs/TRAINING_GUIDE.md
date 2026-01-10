"""
Quick Start Guide for OCR Correction Training
"""

# Step 1: Build vocabulary from training data
print("Step 1: Building vocabulary...")
print("Command: python build_vocab.py")
print()

# Step 2: Start training
print("Step 2: Train the model...")
print("Command: python train.py")
print()

# Step 3: Use trained model for inference
print("Step 3: Use the model...")
print("Command: python infer.py checkpoints/best.ckpt")
print()

print("=" * 60)
print("Training Configuration:")
print("=" * 60)
print("Model: Transformer (Seq2Seq)")
print("Architecture:")
print("  - Encoder: 4 layers, 8 attention heads")
print("  - Decoder: 4 layers, 8 attention heads")
print("  - Embedding dim: 256")
print("  - Feed-forward dim: 1024")
print()
print("Training:")
print("  - Batch size: 16")
print("  - Learning rate: 0.001 (with ReduceLROnPlateau)")
print("  - Loss: CrossEntropyLoss")
print("  - Optimizer: Adam")
print("  - Early stopping: 10 epochs patience")
print("  - Validation split: 10%")
print()
print("Hardware:")
print("  - GPU: CUDA if available, else CPU")
print("  - Mixed precision: Automatic")
print()
print("Monitoring:")
print("  - TensorBoard: tensorboard --logdir=logs")
print("  - Checkpoints: checkpoints/ directory")
print("=" * 60)
