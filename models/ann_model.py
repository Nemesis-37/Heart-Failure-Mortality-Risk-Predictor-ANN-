import torch
import torch.nn as nn


# ============================================================
# STEP 7.1 — DEFINE THE ANN ARCHITECTURE
# ============================================================

class HeartFailureANN(nn.Module):

    def __init__(self):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(11, 64),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(32, 1),
        )

    def forward(self, x):
        """Returns raw unconstrained logits for numerical stability with BCEWithLogitsLoss."""
        return self.network(x)

    def predict_proba(self, x):
        """Convert raw logits to calibrated probabilities in [0, 1]."""
        return torch.sigmoid(self.forward(x))


if __name__ == "__main__":
    # ============================================================
    # STEP 7.2 — TEST THE FORWARD PASS
    # ============================================================

    model = HeartFailureANN()

    # Disable dropout for this test
    model.eval()

    # One sample with 11 input features
    sample_input = torch.randn(1, 11)

    # Generate output logits and probability
    with torch.no_grad():
        output_logits = model(sample_input)
        output_probability = torch.sigmoid(output_logits)

    print("=" * 50)
    print("ANN FORWARD PASS TEST (NUMERICALLY STABLE LOGITS)")
    print("=" * 50)

    print("Input shape:", sample_input.shape)
    print("Output logits shape:", output_logits.shape)
    print("Output raw logit:", output_logits.item())
    print("Output probability via sigmoid:", output_probability.item())

    print("\nForward pass completed successfully.")









