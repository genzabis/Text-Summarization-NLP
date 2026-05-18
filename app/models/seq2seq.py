"""Model Seq2Seq dengan Bahdanau-style attention untuk text summarization.

Arsitektur:
- Encoder: Embedding + Bi-directional GRU
- Attention: additive (Bahdanau)
- Decoder: Embedding + GRU + attention context + linear output

Token khusus:
  <pad> = 0
  <sos> = 1
  <eos> = 2
  <unk> = 3
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


PAD_ID = 0
SOS_ID = 1
EOS_ID = 2
UNK_ID = 3
SPECIAL_TOKENS = ["<pad>", "<sos>", "<eos>", "<unk>"]


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class Encoder(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        emb_dim: int = 128,
        hidden_dim: int = 256,
        num_layers: int = 1,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=PAD_ID)
        self.gru = nn.GRU(
            emb_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        # Reduksi state bi-directional menjadi state decoder uni-directional.
        self.fc = nn.Linear(hidden_dim * 2, hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self, src: torch.Tensor, src_lengths: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        # src: (B, T)
        embedded = self.dropout(self.embedding(src))  # (B, T, E)

        if src_lengths is not None:
            packed = nn.utils.rnn.pack_padded_sequence(
                embedded, src_lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            outputs, hidden = self.gru(packed)
            outputs, _ = nn.utils.rnn.pad_packed_sequence(outputs, batch_first=True)
        else:
            outputs, hidden = self.gru(embedded)

        # outputs: (B, T, 2*H), hidden: (2*L, B, H)
        # Ambil hidden state terakhir dari kedua arah.
        forward_h = hidden[-2]
        backward_h = hidden[-1]
        combined = torch.cat([forward_h, backward_h], dim=1)  # (B, 2H)
        decoder_init = torch.tanh(self.fc(combined)).unsqueeze(0)  # (1, B, H)
        return outputs, decoder_init


# ---------------------------------------------------------------------------
# Bahdanau Attention
# ---------------------------------------------------------------------------

class Attention(nn.Module):
    def __init__(self, hidden_dim: int, enc_hidden_dim: int) -> None:
        super().__init__()
        self.attn = nn.Linear(hidden_dim + enc_hidden_dim * 2, hidden_dim)
        self.v = nn.Linear(hidden_dim, 1, bias=False)

    def forward(
        self,
        decoder_hidden: torch.Tensor,
        encoder_outputs: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        # decoder_hidden: (B, H)
        # encoder_outputs: (B, T, 2H)
        B, T, _ = encoder_outputs.shape
        h = decoder_hidden.unsqueeze(1).expand(-1, T, -1)
        energy = torch.tanh(self.attn(torch.cat([h, encoder_outputs], dim=2)))
        scores = self.v(energy).squeeze(2)  # (B, T)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        return F.softmax(scores, dim=1)


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

class Decoder(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        emb_dim: int = 128,
        hidden_dim: int = 256,
        enc_hidden_dim: int = 256,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=PAD_ID)
        self.attention = Attention(hidden_dim, enc_hidden_dim)
        self.gru = nn.GRU(
            emb_dim + enc_hidden_dim * 2,
            hidden_dim,
            batch_first=True,
        )
        self.fc_out = nn.Linear(hidden_dim + enc_hidden_dim * 2 + emb_dim, vocab_size)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        input_token: torch.Tensor,
        hidden: torch.Tensor,
        encoder_outputs: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # input_token: (B,)
        # hidden: (1, B, H)
        embedded = self.dropout(self.embedding(input_token.unsqueeze(1)))  # (B,1,E)

        attn_weights = self.attention(hidden.squeeze(0), encoder_outputs, mask)  # (B,T)
        context = torch.bmm(attn_weights.unsqueeze(1), encoder_outputs)  # (B,1,2H)

        rnn_input = torch.cat([embedded, context], dim=2)
        output, hidden = self.gru(rnn_input, hidden)  # (B,1,H)

        output = output.squeeze(1)
        context = context.squeeze(1)
        embedded = embedded.squeeze(1)
        logits = self.fc_out(torch.cat([output, context, embedded], dim=1))
        return logits, hidden, attn_weights


# ---------------------------------------------------------------------------
# Seq2Seq wrapper
# ---------------------------------------------------------------------------

class Seq2Seq(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        emb_dim: int = 128,
        hidden_dim: int = 256,
        enc_layers: int = 1,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.encoder = Encoder(vocab_size, emb_dim, hidden_dim, enc_layers, dropout)
        self.decoder = Decoder(vocab_size, emb_dim, hidden_dim, hidden_dim, dropout)

    @staticmethod
    def _make_mask(src: torch.Tensor) -> torch.Tensor:
        return (src != PAD_ID).long()

    def forward(
        self,
        src: torch.Tensor,
        tgt: torch.Tensor,
        src_lengths: Optional[torch.Tensor] = None,
        teacher_forcing_ratio: float = 1.0,
    ) -> torch.Tensor:
        # src: (B, S), tgt: (B, T)
        B, T = tgt.shape
        encoder_outputs, hidden = self.encoder(src, src_lengths)
        mask = self._make_mask(src)

        outputs = torch.zeros(B, T, self.vocab_size, device=src.device)
        input_tok = tgt[:, 0]  # <sos>

        for t in range(1, T):
            logits, hidden, _ = self.decoder(input_tok, hidden, encoder_outputs, mask)
            outputs[:, t] = logits
            use_teacher = torch.rand(1).item() < teacher_forcing_ratio
            input_tok = tgt[:, t] if use_teacher else logits.argmax(1)
        return outputs

    @torch.no_grad()
    def greedy_generate(
        self,
        src: torch.Tensor,
        max_len: int = 80,
        src_lengths: Optional[torch.Tensor] = None,
    ) -> List[List[int]]:
        self.eval()
        encoder_outputs, hidden = self.encoder(src, src_lengths)
        mask = self._make_mask(src)
        B = src.size(0)
        input_tok = torch.full((B,), SOS_ID, dtype=torch.long, device=src.device)
        finished = torch.zeros(B, dtype=torch.bool, device=src.device)
        results: List[List[int]] = [[] for _ in range(B)]

        for _ in range(max_len):
            logits, hidden, _ = self.decoder(input_tok, hidden, encoder_outputs, mask)
            next_tok = logits.argmax(1)
            for i in range(B):
                if not finished[i]:
                    if next_tok[i].item() == EOS_ID:
                        finished[i] = True
                    else:
                        results[i].append(int(next_tok[i].item()))
            if bool(finished.all()):
                break
            input_tok = next_tok
        return results
