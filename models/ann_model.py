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
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.network(x)


if __name__ == "__main__":
    # ============================================================
    # STEP 7.2 — TEST THE FORWARD PASS
    # ============================================================

    model = HeartFailureANN()

    # Disable dropout for this test
    model.eval()

    # One sample with 11 input features
    sample_input = torch.randn(1, 11)

    # Generate output
    with torch.no_grad():
        output_probability = model(sample_input)

    print("=" * 50)
    print("ANN FORWARD PASS TEST")
    print("=" * 50)

    print("Input shape:", sample_input.shape)
    print("Output shape:", output_probability.shape)
    print("Output probability:", output_probability.item())

    print("\nForward pass completed successfully.")









