"""
Training script for OCR Correction Model
"""
import os
import json
import torch
import pytorch_lightning as pl
from pathlib import Path
from torch.utils.data import DataLoader
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import CSVLogger

from .dataset import OCRCorrectionDataset, collate_fn
from .model import OCRCorrectionModel

# Try to import TensorBoard, but fall back to CSV logger if not available
try:
    from pytorch_lightning.loggers import TensorBoardLogger
    TENSORBOARD_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    TENSORBOARD_AVAILABLE = False


def train():
    """Train the OCR correction model"""
    
    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    data_dir = root_dir / "data" / "processed"
    vocab_path = root_dir / "data" / "vocab.json"
    checkpoint_dir = root_dir / "checkpoints"
    log_dir = root_dir / "logs"
    
    # Configuration
    config = {
        "train_path": str(data_dir / "train.json"),
        "val_path": str(data_dir / "validation.json"),
        "test_path": str(data_dir / "test.json"),
        "vocab_path": str(vocab_path),
        "checkpoint_dir": str(checkpoint_dir),
        "log_dir": str(log_dir),
        "max_len": 512,
        "batch_size": 8,  # Adjusted for RTX 3050 6GB
        "num_workers": 0,  # Set to 0 to avoid multiprocessing issues on Windows
        
        # Model hyperparameters
        "d_model": 256,  # Increased for larger dataset
        "nhead": 8,
        "num_encoder_layers": 4,
        "num_decoder_layers": 4,
        "dim_feedforward": 1024,
        "dropout": 0.1,
        "learning_rate": 0.0001,  # Reduced 10x to prevent gradient explosion
        
        # Training parameters
        "max_epochs": 50,
        "patience": 10,
        "accelerator": "gpu" if torch.cuda.is_available() else "cpu",
        "devices": 1
    }
    
    print("=" * 60)
    print("OCR Correction Model Training")
    print("=" * 60)
    print(f"Device: {config['accelerator']}")
    
    # Check if vocab exists
    if not os.path.exists(config["vocab_path"]):
        print("\n❌ vocab.json not found!")
        print("Run: python src/utils/build_vocab.py")
        return
    
    # Load datasets
    print("\n📚 Loading datasets...")
    train_dataset = OCRCorrectionDataset(
        data_path=config["train_path"],
        vocab_path=config["vocab_path"],
        max_len=config["max_len"]
    )
    
    val_dataset = OCRCorrectionDataset(
        data_path=config["val_path"],
        vocab_path=config["vocab_path"],
        max_len=config["max_len"]
    )
    
    print(f"\n✅ Train samples: {len(train_dataset):,}")
    print(f"✅ Validation samples: {len(val_dataset):,}")
    
    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config["batch_size"],
        shuffle=True,
        num_workers=config["num_workers"],
        collate_fn=collate_fn,
        pin_memory=True if torch.cuda.is_available() else False
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config["batch_size"],
        shuffle=False,
        num_workers=config["num_workers"],
        collate_fn=collate_fn,
        pin_memory=True if torch.cuda.is_available() else False
    )
    
    # Create model
    print("\n🤖 Creating model...")
    model = OCRCorrectionModel(
        vocab_size=train_dataset.vocab_size,
        d_model=config["d_model"],
        nhead=config["nhead"],
        num_encoder_layers=config["num_encoder_layers"],
        num_decoder_layers=config["num_decoder_layers"],
        dim_feedforward=config["dim_feedforward"],
        dropout=config["dropout"],
        learning_rate=config["learning_rate"],
        pad_idx=train_dataset.pad_idx
    )
    
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Create directories
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath=config["checkpoint_dir"],
        filename="ocr-correction-{epoch:02d}-{val_loss:.4f}",
        monitor="val_loss",
        mode="min",
        save_top_k=3,
        save_last=True,
        verbose=True
    )
    
    early_stop_callback = EarlyStopping(
        monitor="val_loss",
        patience=config["patience"],
        mode="min",
        verbose=True
    )
    
    lr_monitor = LearningRateMonitor(logging_interval='epoch')
    
    # Logger
    if TENSORBOARD_AVAILABLE:
        logger = TensorBoardLogger(config["log_dir"], name="ocr_correction")
        print("\n📊 Using TensorBoard logger")
        print(f"   View logs: tensorboard --logdir={config['log_dir']}")
    else:
        logger = CSVLogger(config["log_dir"], name="ocr_correction")
        print("\n📊 Using CSV logger (TensorBoard not available)")
        print("   Install TensorBoard: pip install tensorboard")
        print(f"   Logs saved to: {config['log_dir']}/ocr_correction/")
    
    # Trainer
    print("\n🚀 Starting training...")
    trainer = pl.Trainer(
        max_epochs=config["max_epochs"],
        accelerator=config["accelerator"],
        devices=config["devices"],
        callbacks=[checkpoint_callback, early_stop_callback, lr_monitor],
        logger=logger,
        gradient_clip_val=1.0,
        log_every_n_steps=10,
        deterministic=False
    )
    
    # Train
    trainer.fit(model, train_loader, val_loader)
    
    print("\n" + "=" * 60)
    print("✅ Training completed!")
    print(f"📈 Best validation loss: {checkpoint_callback.best_model_score:.4f}")
    print(f"💾 Best checkpoint: {checkpoint_callback.best_model_path}")
    if TENSORBOARD_AVAILABLE:
        print("\n📊 To view training logs:")
        print(f"  tensorboard --logdir={config['log_dir']}")
    else:
        print(f"\n📊 Training logs saved to: {config['log_dir']}/ocr_correction/")
        print("Install TensorBoard to visualize: pip install tensorboard")
    print("=" * 60)
    
    # Save config
    config_path = checkpoint_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n⚙️  Configuration saved to: {config_path}")


if __name__ == "__main__":
    train()
