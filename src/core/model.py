"""
Transformer-based OCR Correction Model using PyTorch Lightning
"""
import torch
import torch.nn as nn
import pytorch_lightning as pl
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
import json


class OCRCorrectionModel(pl.LightningModule):
    """
    Transformer-based sequence-to-sequence model for OCR correction
    """
    
    def __init__(
        self,
        vocab_size,
        d_model=256,
        nhead=8,
        num_encoder_layers=4,
        num_decoder_layers=4,
        dim_feedforward=1024,
        dropout=0.1,
        learning_rate=0.001,
        pad_idx=0
    ):
        super().__init__()
        self.save_hyperparameters()
        
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.pad_idx = pad_idx
        self.learning_rate = learning_rate
        
        # Embedding layers
        self.src_embedding = nn.Embedding(vocab_size, d_model, padding_idx=pad_idx)
        self.tgt_embedding = nn.Embedding(vocab_size, d_model, padding_idx=pad_idx)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, dropout)
        
        # Transformer
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        
        # Output layer
        self.fc_out = nn.Linear(d_model, vocab_size)
        
        # Loss function
        self.criterion = nn.CrossEntropyLoss(ignore_index=pad_idx, label_smoothing=0.1)
        
    def forward(self, src, tgt):
        """
        Args:
            src: Source sequence (batch_size, src_len)
            tgt: Target sequence (batch_size, tgt_len)
        Returns:
            output: (batch_size, tgt_len, vocab_size)
        """
        # Create masks
        src_mask = self._generate_square_subsequent_mask(src.size(1)).to(src.device)
        tgt_mask = self._generate_square_subsequent_mask(tgt.size(1)).to(tgt.device)
        
        src_padding_mask = (src == self.pad_idx)
        tgt_padding_mask = (tgt == self.pad_idx)
        
        # Embeddings
        src_emb = self.pos_encoder(self.src_embedding(src) * (self.d_model ** 0.5))
        tgt_emb = self.pos_encoder(self.tgt_embedding(tgt) * (self.d_model ** 0.5))
        
        # Transformer
        output = self.transformer(
            src_emb,
            tgt_emb,
            src_mask=None,  # Encoder can see all input
            tgt_mask=tgt_mask,  # Decoder uses causal mask
            memory_mask=None,
            src_key_padding_mask=src_padding_mask,
            tgt_key_padding_mask=tgt_padding_mask,
            memory_key_padding_mask=src_padding_mask
        )
        
        # Project to vocabulary
        output = self.fc_out(output)
        
        return output
    
    def _generate_square_subsequent_mask(self, sz):
        """Generate causal mask for decoder"""
        mask = torch.triu(torch.ones(sz, sz), diagonal=1)
        mask = mask.masked_fill(mask == 1, float('-inf'))
        return mask
    
    def training_step(self, batch, batch_idx):
        """Training step"""
        src = batch["input"]
        tgt = batch["target"]
        
        # Forward pass (exclude last token of target for input)
        tgt_input = tgt[:, :-1]
        output = self(src, tgt_input)
        
        # Calculate loss (exclude first token of target for comparison)
        tgt_output = tgt[:, 1:]
        loss = self.criterion(output.reshape(-1, self.vocab_size), tgt_output.reshape(-1))
        
        # Check for NaN or Inf loss
        if torch.isnan(loss) or torch.isinf(loss):
            print(f"WARNING: Invalid loss detected at batch {batch_idx}")
            return None
        
        # Log metrics
        self.log('train_loss', loss, prog_bar=True, on_step=True, on_epoch=True)
        
        return loss
    
    def validation_step(self, batch, batch_idx):
        """Validation step"""
        src = batch["input"]
        tgt = batch["target"]
        
        # Forward pass
        tgt_input = tgt[:, :-1]
        output = self(src, tgt_input)
        
        # Calculate loss
        tgt_output = tgt[:, 1:]
        loss = self.criterion(output.reshape(-1, self.vocab_size), tgt_output.reshape(-1))
        
        # Log metrics
        self.log('val_loss', loss, prog_bar=True)
        
        return loss
    
    def configure_optimizers(self):
        """Configure optimizer and scheduler"""
        optimizer = Adam(self.parameters(), lr=self.learning_rate)
        scheduler = ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=3,
            verbose=True
        )
        
        return {
            'optimizer': optimizer,
            'lr_scheduler': {
                'scheduler': scheduler,
                'monitor': 'val_loss'
            }
        }
    
    @torch.no_grad()
    def generate(self, src, max_len=512, sos_idx=1, eos_idx=2):
        """
        Generate corrected text using greedy decoding
        
        Args:
            src: Source sequence (batch_size, src_len)
            max_len: Maximum generation length
            sos_idx: Start of sequence token index
            eos_idx: End of sequence token index
        
        Returns:
            Generated sequence (batch_size, gen_len)
        """
        self.eval()
        batch_size = src.size(0)
        device = src.device
        
        # Encode source
        src_padding_mask = (src == self.pad_idx)
        src_emb = self.pos_encoder(self.src_embedding(src) * (self.d_model ** 0.5))
        memory = self.transformer.encoder(src_emb, src_key_padding_mask=src_padding_mask)
        
        # Initialize decoder input with SOS token
        tgt = torch.full((batch_size, 1), sos_idx, dtype=torch.long, device=device)
        
        for _ in range(max_len):
            # Create decoder mask
            tgt_mask = self._generate_square_subsequent_mask(tgt.size(1)).to(device)
            
            # Decode
            tgt_emb = self.pos_encoder(self.tgt_embedding(tgt) * (self.d_model ** 0.5))
            output = self.transformer.decoder(
                tgt_emb,
                memory,
                tgt_mask=tgt_mask,
                memory_key_padding_mask=src_padding_mask
            )
            
            # Get next token prediction
            logits = self.fc_out(output[:, -1, :])
            next_token = logits.argmax(dim=-1, keepdim=True)
            
            # Append to sequence
            tgt = torch.cat([tgt, next_token], dim=1)
            
            # Stop if all sequences generated EOS
            if (next_token == eos_idx).all():
                break
        
        return tgt


class PositionalEncoding(nn.Module):
    """Positional encoding for transformer"""
    
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # Create positional encoding matrix
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-torch.log(torch.tensor(10000.0)) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        """Add positional encoding to input"""
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)
