"""
Phase 8: L-BFGS Optimizer, Feature Ablation and Probability Calibration
Heart Failure Mortality Risk Predictor

Experiments:
  1. Optimizer comparison: Adam vs full-batch L-BFGS (Standard + Log1p preprocessing)
  2. Feature ablation: 11 features, -diabetes, -sex, -smoking, -all three
  3. Probability calibration: Raw, Platt scaling, Temperature scaling

Constraints:
  - Identical StratifiedKFold(n_splits=5, shuffle=True, random_state=42) for all models
  - No data leakage: scalers, log transforms and calibrators fitted on training fold only
  - Outer test folds never used for model selection, threshold selection or calibration fitting
  - Production checkpoint models/ann_model.pth is NOT modified
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
from scipy.stats import wilcoxon
from scipy.special import expit  # sigmoid

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

# ── Paths ────────────────────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(WORKSPACE, "dataset", "heart_failure_clinical_records_dataset.csv")
RESULTS_DIR = os.path.join(WORKSPACE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Data ─────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
TARGET = "DEATH_EVENT"
DROP = ["DEATH_EVENT", "time"]
ALL_FEATURES = [c for c in df.columns if c not in DROP]  # 11 features
y_all = df[TARGET].values.astype(np.float32)
X_all = df[ALL_FEATURES].values.astype(np.float32)

FEATURE_NAMES = ALL_FEATURES
NOISE_FEATURES = ["diabetes", "sex", "smoking"]
NOISE_IDX = [FEATURE_NAMES.index(f) for f in NOISE_FEATURES]

print(f"Dataset: {len(df)} patients, {len(ALL_FEATURES)} features, {int(y_all.sum())} deaths")
print(f"Features: {ALL_FEATURES}")
print(f"Noise feature indices to ablate: {NOISE_IDX} ({NOISE_FEATURES})")

# ── Cross-validation folds ───────────────────────────────────────────────────
CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

# ── Architecture ─────────────────────────────────────────────────────────────
class WidDeepANN(nn.Module):
    """Wide & Deep: linear branch + small MLP branch."""
    def __init__(self, n_features, hidden=8, dropout=0.2):
        super().__init__()
        self.linear_branch = nn.Linear(n_features, 1, bias=True)
        self.deep = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1, bias=True),
        )
        self._init_weights()

    def _init_weights(self):
        nn.init.xavier_uniform_(self.linear_branch.weight)
        nn.init.zeros_(self.linear_branch.bias)
        for m in self.deep:
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        return self.linear_branch(x) + self.deep(x)


# ── Metric helpers ────────────────────────────────────────────────────────────
def compute_metrics(y_true, y_prob, threshold=0.50):
    auroc = roc_auc_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    ll = log_loss(y_true, y_prob)
    y_pred = (y_prob >= threshold).astype(int)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * prec * sens / (prec + sens) if (prec + sens) > 0 else 0.0
    return dict(auroc=auroc, brier=brier, log_loss=ll,
                sensitivity=sens, specificity=spec,
                precision=prec, f1=f1,
                tp=tp, fp=fp, tn=tn, fn=fn)


def calibration_slope_intercept(y_true, y_prob):
    """Fit logit(y_prob) ~ intercept + slope*logit(y_prob) on outer test."""
    logits = np.log(np.clip(y_prob, 1e-7, 1 - 1e-7) /
                    (1 - np.clip(y_prob, 1e-7, 1 - 1e-7)))
    try:
        lr = LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000)
        lr.fit(logits.reshape(-1, 1), y_true)
        return float(lr.coef_[0][0]), float(lr.intercept_[0])
    except Exception:
        return float("nan"), float("nan")


def expected_calibration_error(y_true, y_prob, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    bin_data = []
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if mask.sum() == 0:
            bin_data.append(dict(bin_low=bins[i], bin_high=bins[i+1], count=0,
                                 mean_pred=float("nan"), mean_true=float("nan"),
                                 contribution=0.0))
            continue
        m_pred = y_prob[mask].mean()
        m_true = y_true[mask].mean()
        contrib = (mask.sum() / n) * abs(m_pred - m_true)
        ece += contrib
        bin_data.append(dict(bin_low=round(bins[i], 2), bin_high=round(bins[i+1], 2),
                             count=int(mask.sum()),
                             mean_pred=round(m_pred, 4), mean_true=round(m_true, 4),
                             contribution=round(contrib, 6)))
    return ece, bin_data


# ── Preprocessing ─────────────────────────────────────────────────────────────
def preprocess(X_train, X_val, use_log=False, feature_mask=None):
    """Apply optional log1p then StandardScaler. feature_mask selects columns."""
    if feature_mask is not None:
        X_train = X_train[:, feature_mask]
        X_val = X_val[:, feature_mask]
    if use_log:
        # CPK and serum_creatinine indices in the feature list
        cpk_idx = ALL_FEATURES.index("creatinine_phosphokinase")
        sc_idx = ALL_FEATURES.index("serum_creatinine")
        # Remap to masked-feature space
        if feature_mask is not None:
            new_cpk = list(feature_mask).index(cpk_idx) if cpk_idx in feature_mask else None
            new_sc = list(feature_mask).index(sc_idx) if sc_idx in feature_mask else None
        else:
            new_cpk, new_sc = cpk_idx, sc_idx
        X_train = X_train.copy()
        X_val = X_val.copy()
        if new_cpk is not None:
            X_train[:, new_cpk] = np.log1p(X_train[:, new_cpk])
            X_val[:, new_cpk] = np.log1p(X_val[:, new_cpk])
        if new_sc is not None:
            X_train[:, new_sc] = np.log1p(X_train[:, new_sc])
            X_val[:, new_sc] = np.log1p(X_val[:, new_sc])
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    return X_train.astype(np.float32), X_val.astype(np.float32)


# ── Adam training ─────────────────────────────────────────────────────────────
def train_adam(model, X_tr, y_tr, X_stop, y_stop,
               weight_decay=0.01, batch_size=32, max_epochs=200, patience=15):
    criterion = nn.BCEWithLogitsLoss()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=weight_decay)
    Xtr_t = torch.tensor(X_tr)
    ytr_t = torch.tensor(y_tr).unsqueeze(1)
    Xs_t = torch.tensor(X_stop)
    ys_t = torch.tensor(y_stop).unsqueeze(1)
    loader = DataLoader(TensorDataset(Xtr_t, ytr_t), batch_size=batch_size, shuffle=True,
                        generator=torch.Generator().manual_seed(SEED))
    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0
    train_losses, val_losses = [], []
    for epoch in range(max_epochs):
        model.train()
        ep_loss = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            opt.step()
            ep_loss += loss.item() * len(xb)
        ep_loss /= len(X_tr)
        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(Xs_t), ys_t).item()
        train_losses.append(ep_loss)
        val_losses.append(val_loss)
        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
        if patience_counter >= patience:
            break
    if best_state:
        model.load_state_dict(best_state)
    # Step-adjusted refit on full training fold
    all_X = np.concatenate([X_tr, X_stop], axis=0)
    all_y = np.concatenate([y_tr, y_stop], axis=0)
    opt2 = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=weight_decay)
    loader2 = DataLoader(TensorDataset(torch.tensor(all_X), torch.tensor(all_y).unsqueeze(1)),
                         batch_size=batch_size, shuffle=True,
                         generator=torch.Generator().manual_seed(SEED))
    best_epoch = len(train_losses)
    steps_per_epoch_orig = max(1, len(X_tr) // batch_size)
    steps_per_epoch_full = max(1, len(all_X) // batch_size)
    refit_epochs = round(best_epoch * steps_per_epoch_orig / steps_per_epoch_full)
    model.train()
    for _ in range(max(1, refit_epochs)):
        for xb, yb in loader2:
            opt2.zero_grad()
            criterion(model(xb), yb).backward()
            opt2.step()
    model.eval()
    return model, train_losses, val_losses, best_epoch


# ── L-BFGS training ───────────────────────────────────────────────────────────
def train_lbfgs(model, X_tr, y_tr, X_stop, y_stop,
                weight_decay=0.01, max_iter=50, patience=10):
    """Full-batch L-BFGS with strong Wolfe line search."""
    criterion = nn.BCEWithLogitsLoss()
    opt = torch.optim.LBFGS(model.parameters(), lr=0.5, max_iter=20,
                             history_size=10, line_search_fn="strong_wolfe")
    Xtr_t = torch.tensor(X_tr)
    ytr_t = torch.tensor(y_tr).unsqueeze(1)
    Xs_t = torch.tensor(X_stop)
    ys_t = torch.tensor(y_stop).unsqueeze(1)

    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0
    train_losses, val_losses = [], []

    for iteration in range(max_iter):
        def closure():
            opt.zero_grad()
            logits = model(Xtr_t)
            loss = criterion(logits, ytr_t)
            # L2 regularisation (weight decay applied manually for L-BFGS)
            l2 = sum((p ** 2).sum() for p in model.parameters())
            total = loss + 0.5 * weight_decay * l2
            total.backward()
            return total

        model.train()
        opt.step(closure)

        model.eval()
        with torch.no_grad():
            train_logits = model(Xtr_t)
            train_loss_val = criterion(train_logits, ytr_t).item()
            val_logits = model(Xs_t)
            val_loss = criterion(val_logits, ys_t).item()

        train_losses.append(train_loss_val)
        val_losses.append(val_loss)

        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= patience:
            break

    if best_state:
        model.load_state_dict(best_state)

    # Refit on full training fold
    all_X = np.concatenate([X_tr, X_stop], axis=0)
    all_y = np.concatenate([y_tr, y_stop], axis=0)
    Xall_t = torch.tensor(all_X)
    yall_t = torch.tensor(all_y).unsqueeze(1)
    opt2 = torch.optim.LBFGS(model.parameters(), lr=0.5, max_iter=20,
                              history_size=10, line_search_fn="strong_wolfe")
    best_iter = len(train_losses)
    for _ in range(max(1, best_iter)):
        def closure2():
            opt2.zero_grad()
            logits = model(Xall_t)
            loss = criterion(logits, yall_t)
            l2 = sum((p ** 2).sum() for p in model.parameters())
            total = loss + 0.5 * weight_decay * l2
            total.backward()
            return total
        model.train()
        opt2.step(closure2)

    model.eval()
    return model, train_losses, val_losses, len(train_losses)


# ── Predict ───────────────────────────────────────────────────────────────────
def predict_proba(model, X):
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor(X))
    return torch.sigmoid(logits).numpy().flatten()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 1: Optimizer Comparison
# Models: WideDeep + Adam + Standard, WideDeep + Adam + Log1p,
#         WideDeep + L-BFGS + Standard, WideDeep + L-BFGS + Log1p
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("EXPERIMENT 1: Optimizer Comparison (Adam vs L-BFGS)")
print("="*70)

EXP1_CONFIGS = [
    dict(id="WD_Adam_Standard",    optimizer="adam",  use_log=False),
    dict(id="WD_Adam_Log1p",       optimizer="adam",  use_log=True),
    dict(id="WD_LBFGS_Standard",   optimizer="lbfgs", use_log=False),
    dict(id="WD_LBFGS_Log1p",      optimizer="lbfgs", use_log=True),
]

exp1_fold_records = []
exp1_oof_preds = {cfg["id"]: np.zeros(len(y_all)) for cfg in EXP1_CONFIGS}

for cfg in EXP1_CONFIGS:
    print(f"\n  → {cfg['id']}")
    fold_aurocs = []
    for fold_idx, (train_idx, test_idx) in enumerate(CV.split(X_all, y_all)):
        torch.manual_seed(SEED + fold_idx)
        np.random.seed(SEED + fold_idx)

        X_train_full = X_all[train_idx]
        y_train_full = y_all[train_idx]
        X_test = X_all[test_idx]
        y_test = y_all[test_idx]

        # Inner split for early stopping (20%)
        X_tr, X_stop, y_tr, y_stop = train_test_split(
            X_train_full, y_train_full, test_size=0.2,
            stratify=y_train_full, random_state=SEED)

        # Preprocess (fit on X_tr only)
        X_tr_p, X_stop_p = preprocess(X_tr, X_stop, use_log=cfg["use_log"])
        _, X_test_p = preprocess(X_tr, X_test, use_log=cfg["use_log"])

        n_features = X_tr_p.shape[1]
        model = WidDeepANN(n_features=n_features, hidden=8, dropout=0.2)

        if cfg["optimizer"] == "adam":
            model, tr_losses, val_losses, best_ep = train_adam(
                model, X_tr_p, y_tr, X_stop_p, y_stop,
                weight_decay=0.01, batch_size=32, max_epochs=200, patience=15)
        else:
            model, tr_losses, val_losses, best_ep = train_lbfgs(
                model, X_tr_p, y_tr, X_stop_p, y_stop,
                weight_decay=0.01, max_iter=50, patience=10)

        y_prob = predict_proba(model, X_test_p)
        exp1_oof_preds[cfg["id"]][test_idx] = y_prob
        m = compute_metrics(y_test, y_prob)
        cal_slope, cal_int = calibration_slope_intercept(y_test, y_prob)

        fold_aurocs.append(m["auroc"])
        exp1_fold_records.append(dict(
            experiment="optimizer", model_id=cfg["id"],
            optimizer=cfg["optimizer"], use_log=cfg["use_log"],
            fold=fold_idx + 1, n_test=len(y_test),
            n_pos=int(y_test.sum()), n_neg=int((1 - y_test).sum()),
            best_epoch=best_ep, final_train_loss=round(tr_losses[-1], 6),
            final_val_loss=round(val_losses[-1], 6),
            auroc=round(m["auroc"], 6), brier=round(m["brier"], 6),
            log_loss=round(m["log_loss"], 6),
            sensitivity=round(m["sensitivity"], 6),
            specificity=round(m["specificity"], 6),
            precision=round(m["precision"], 6), f1=round(m["f1"], 6),
            tp=m["tp"], fp=m["fp"], tn=m["tn"], fn=m["fn"],
            cal_slope=round(cal_slope, 6), cal_intercept=round(cal_int, 6)
        ))
        print(f"    Fold {fold_idx+1}: AUROC={m['auroc']:.4f}  Brier={m['brier']:.4f}  "
              f"Sens={m['sensitivity']:.4f}  ep={best_ep}  val_loss={val_losses[-1]:.4f}")
    print(f"    Mean AUROC: {np.mean(fold_aurocs):.4f} ± {np.std(fold_aurocs):.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 2: Feature Ablation
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("EXPERIMENT 2: Feature Ablation")
print("="*70)

diabetes_idx = ALL_FEATURES.index("diabetes")
sex_idx = ALL_FEATURES.index("sex")
smoking_idx = ALL_FEATURES.index("smoking")

ABLATION_CONFIGS = [
    dict(id="Ablation_All11",           remove=[],                              label="All 11 features"),
    dict(id="Ablation_NoDiabetes",      remove=[diabetes_idx],                  label="Without diabetes"),
    dict(id="Ablation_NoSex",           remove=[sex_idx],                       label="Without sex"),
    dict(id="Ablation_NoSmoking",       remove=[smoking_idx],                   label="Without smoking"),
    dict(id="Ablation_NoNoise",         remove=[diabetes_idx, sex_idx, smoking_idx], label="Without all 3 noise features"),
]

exp2_fold_records = []
exp2_oof_preds = {cfg["id"]: np.zeros(len(y_all)) for cfg in ABLATION_CONFIGS}

for cfg in ABLATION_CONFIGS:
    # Feature mask: indices to KEEP
    keep_idx = [i for i in range(len(ALL_FEATURES)) if i not in cfg["remove"]]
    n_features = len(keep_idx)
    print(f"\n  → {cfg['id']} ({cfg['label']}, {n_features} features)")

    fold_aurocs = []
    for fold_idx, (train_idx, test_idx) in enumerate(CV.split(X_all, y_all)):
        torch.manual_seed(SEED + fold_idx)
        np.random.seed(SEED + fold_idx)

        X_train_full = X_all[train_idx][:, keep_idx]
        y_train_full = y_all[train_idx]
        X_test = X_all[test_idx][:, keep_idx]
        y_test = y_all[test_idx]

        X_tr, X_stop, y_tr, y_stop = train_test_split(
            X_train_full, y_train_full, test_size=0.2,
            stratify=y_train_full, random_state=SEED)

        # Log1p on remapped indices (best preprocessing from Exp1 uses log1p)
        # Remap CPK and serum_creatinine to new column positions
        try:
            new_cpk = keep_idx.index(ALL_FEATURES.index("creatinine_phosphokinase"))
            new_sc = keep_idx.index(ALL_FEATURES.index("serum_creatinine"))
        except ValueError:
            new_cpk, new_sc = None, None

        def apply_log1p_manual(X, cpk_i, sc_i):
            X = X.copy()
            if cpk_i is not None:
                X[:, cpk_i] = np.log1p(X[:, cpk_i])
            if sc_i is not None:
                X[:, sc_i] = np.log1p(X[:, sc_i])
            return X

        X_tr_l = apply_log1p_manual(X_tr, new_cpk, new_sc)
        X_stop_l = apply_log1p_manual(X_stop, new_cpk, new_sc)
        X_test_l = apply_log1p_manual(X_test, new_cpk, new_sc)

        scaler = StandardScaler()
        X_tr_p = scaler.fit_transform(X_tr_l).astype(np.float32)
        X_stop_p = scaler.transform(X_stop_l).astype(np.float32)
        X_test_p = scaler.transform(X_test_l).astype(np.float32)

        # Use best optimizer from Exp1 (L-BFGS, log1p)
        model = WidDeepANN(n_features=n_features, hidden=8, dropout=0.2)
        model, tr_losses, val_losses, best_ep = train_lbfgs(
            model, X_tr_p, y_tr, X_stop_p, y_stop,
            weight_decay=0.01, max_iter=50, patience=10)

        y_prob = predict_proba(model, X_test_p)
        exp2_oof_preds[cfg["id"]][test_idx] = y_prob
        m = compute_metrics(y_test, y_prob)
        cal_slope, cal_int = calibration_slope_intercept(y_test, y_prob)

        fold_aurocs.append(m["auroc"])
        exp2_fold_records.append(dict(
            experiment="ablation", model_id=cfg["id"], label=cfg["label"],
            n_features=n_features, removed=str([ALL_FEATURES[i] for i in cfg["remove"]]),
            fold=fold_idx + 1, n_test=len(y_test),
            n_pos=int(y_test.sum()), n_neg=int((1 - y_test).sum()),
            best_epoch=best_ep,
            auroc=round(m["auroc"], 6), brier=round(m["brier"], 6),
            log_loss=round(m["log_loss"], 6),
            sensitivity=round(m["sensitivity"], 6),
            specificity=round(m["specificity"], 6),
            precision=round(m["precision"], 6), f1=round(m["f1"], 6),
            tp=m["tp"], fp=m["fp"], tn=m["tn"], fn=m["fn"],
            cal_slope=round(cal_slope, 6), cal_intercept=round(cal_int, 6)
        ))
        print(f"    Fold {fold_idx+1}: AUROC={m['auroc']:.4f}  Brier={m['brier']:.4f}  "
              f"Sens={m['sensitivity']:.4f}  ep={best_ep}")
    print(f"    Mean AUROC: {np.mean(fold_aurocs):.4f} ± {np.std(fold_aurocs):.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 3: Probability Calibration
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("EXPERIMENT 3: Probability Calibration")
print("="*70)

# We calibrate the best ANN variant from Exp 1 (WD_LBFGS_Log1p)
# and also LR for reference.
# Calibrators are fitted on inner-validation predictions, evaluated on outer test.

class PlattScaler:
    """Platt scaling: sigmoid(a * logit + b) fitted via LR on val logits."""
    def __init__(self):
        self.a = 1.0
        self.b = 0.0

    def fit(self, y_val, p_val):
        logits = np.log(np.clip(p_val, 1e-7, 1-1e-7) / (1 - np.clip(p_val, 1e-7, 1-1e-7)))
        lr = LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000)
        lr.fit(logits.reshape(-1, 1), y_val)
        self.a = float(lr.coef_[0][0])
        self.b = float(lr.intercept_[0])
        return self

    def predict(self, p_test):
        logits = np.log(np.clip(p_test, 1e-7, 1-1e-7) / (1 - np.clip(p_test, 1e-7, 1-1e-7)))
        return expit(self.a * logits + self.b)


class TemperatureScaler:
    """Temperature scaling: sigmoid(logit / T), T fitted on val NLL."""
    def __init__(self):
        self.T = 1.0

    def fit(self, y_val, p_val):
        logits_v = np.log(np.clip(p_val, 1e-7, 1-1e-7) / (1 - np.clip(p_val, 1e-7, 1-1e-7)))
        y_t = torch.tensor(y_val, dtype=torch.float32)
        logits_t = torch.tensor(logits_v, dtype=torch.float32)
        T_param = torch.nn.Parameter(torch.ones(1))
        opt = torch.optim.LBFGS([T_param], lr=0.01, max_iter=50,
                                 line_search_fn="strong_wolfe")
        criterion = nn.BCEWithLogitsLoss()
        def closure():
            opt.zero_grad()
            scaled = logits_t / T_param.clamp(min=0.05)
            loss = criterion(scaled.unsqueeze(1), y_t.unsqueeze(1))
            loss.backward()
            return loss
        opt.step(closure)
        self.T = float(T_param.item())
        return self

    def predict(self, p_test):
        logits = np.log(np.clip(p_test, 1e-7, 1-1e-7) / (1 - np.clip(p_test, 1e-7, 1-1e-7)))
        return expit(logits / max(self.T, 0.05))


# Calibration models to evaluate: LR (baseline) and WD_LBFGS_Log1p
CAL_MODELS = [
    dict(id="LR_Raw",           base="LR",            cal="raw"),
    dict(id="WD_LBFGS_Log_Raw", base="WD_LBFGS_Log1p", cal="raw"),
    dict(id="WD_LBFGS_Log_Platt", base="WD_LBFGS_Log1p", cal="platt"),
    dict(id="WD_LBFGS_Log_Temp",  base="WD_LBFGS_Log1p", cal="temperature"),
]

exp3_fold_records = []
exp3_oof_preds = {cfg["id"]: np.zeros(len(y_all)) for cfg in CAL_MODELS}
exp3_ece_records = []

for cfg in CAL_MODELS:
    print(f"\n  → {cfg['id']}")
    fold_aurocs = []

    for fold_idx, (train_idx, test_idx) in enumerate(CV.split(X_all, y_all)):
        torch.manual_seed(SEED + fold_idx)
        np.random.seed(SEED + fold_idx)

        X_train_full = X_all[train_idx]
        y_train_full = y_all[train_idx]
        X_test = X_all[test_idx]
        y_test = y_all[test_idx]

        X_tr, X_stop, y_tr, y_stop = train_test_split(
            X_train_full, y_train_full, test_size=0.2,
            stratify=y_train_full, random_state=SEED)

        if cfg["base"] == "LR":
            # Fit scaler on X_tr, transform all
            scaler = StandardScaler()
            X_tr_p = scaler.fit_transform(X_tr).astype(np.float32)
            X_stop_p = scaler.transform(X_stop).astype(np.float32)
            X_test_p = scaler.transform(X_test).astype(np.float32)

            lr_model = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs",
                                          max_iter=1000, random_state=SEED)
            lr_model.fit(X_tr_p, y_tr)
            # Val predictions for calibration fitting
            p_val = lr_model.predict_proba(X_stop_p)[:, 1]
            p_test = lr_model.predict_proba(X_test_p)[:, 1]

        else:  # WD_LBFGS_Log1p
            X_tr_p, X_stop_p = preprocess(X_tr, X_stop, use_log=True)
            _, X_test_p = preprocess(X_tr, X_test, use_log=True)
            model = WidDeepANN(n_features=11, hidden=8, dropout=0.2)
            model, _, _, _ = train_lbfgs(model, X_tr_p, y_tr, X_stop_p, y_stop,
                                          weight_decay=0.01, max_iter=50, patience=10)
            p_val = predict_proba(model, X_stop_p)
            p_test = predict_proba(model, X_test_p)

        # Apply calibration (fitted on val set only)
        if cfg["cal"] == "raw":
            p_cal = p_test
            cal_name = "none"
            T_val = float("nan")
            platt_a = float("nan")
            platt_b = float("nan")
        elif cfg["cal"] == "platt":
            ps = PlattScaler().fit(y_stop, p_val)
            p_cal = ps.predict(p_test)
            cal_name = "platt"
            T_val = float("nan")
            platt_a = ps.a
            platt_b = ps.b
        elif cfg["cal"] == "temperature":
            ts = TemperatureScaler().fit(y_stop, p_val)
            p_cal = ts.predict(p_test)
            cal_name = "temperature"
            T_val = ts.T
            platt_a = float("nan")
            platt_b = float("nan")

        exp3_oof_preds[cfg["id"]][test_idx] = p_cal
        m = compute_metrics(y_test, p_cal)
        cal_slope, cal_int = calibration_slope_intercept(y_test, p_cal)
        ece, bin_data = expected_calibration_error(y_test, p_cal, n_bins=10)

        fold_aurocs.append(m["auroc"])
        exp3_fold_records.append(dict(
            experiment="calibration", model_id=cfg["id"],
            base_model=cfg["base"], calibration=cfg["cal"],
            fold=fold_idx + 1, n_test=len(y_test),
            n_pos=int(y_test.sum()), n_neg=int((1 - y_test).sum()),
            auroc=round(m["auroc"], 6), brier=round(m["brier"], 6),
            log_loss=round(m["log_loss"], 6),
            sensitivity=round(m["sensitivity"], 6),
            specificity=round(m["specificity"], 6),
            precision=round(m["precision"], 6), f1=round(m["f1"], 6),
            tp=m["tp"], fp=m["fp"], tn=m["tn"], fn=m["fn"],
            cal_slope=round(cal_slope, 6), cal_intercept=round(cal_int, 6),
            ece=round(ece, 6),
            temperature=round(T_val, 6) if not np.isnan(T_val) else float("nan"),
            platt_a=round(platt_a, 6) if not np.isnan(platt_a) else float("nan"),
            platt_b=round(platt_b, 6) if not np.isnan(platt_b) else float("nan"),
        ))
        for bd in bin_data:
            exp3_ece_records.append(dict(
                model_id=cfg["id"], fold=fold_idx + 1, **bd))
        print(f"    Fold {fold_idx+1}: AUROC={m['auroc']:.4f}  Brier={m['brier']:.4f}  "
              f"ECE={ece:.4f}  CalSlope={cal_slope:.4f}  cal={cfg['cal']}")
    print(f"    Mean AUROC: {np.mean(fold_aurocs):.4f} ± {np.std(fold_aurocs):.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD SUMMARY TABLES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("BUILDING SUMMARY TABLES")
print("="*70)

def summarize_folds(records, id_col="model_id"):
    df_r = pd.DataFrame(records)
    rows = []
    for mid in df_r[id_col].unique():
        sub = df_r[df_r[id_col] == mid]
        row = {id_col: mid}
        for col in ["auroc", "brier", "log_loss", "sensitivity", "specificity",
                    "precision", "f1", "cal_slope", "cal_intercept"]:
            if col in sub.columns:
                row[f"{col}_mean"] = round(sub[col].mean(), 6)
                row[f"{col}_std"] = round(sub[col].std(ddof=1), 6)
        for col in ["tp", "fp", "tn", "fn"]:
            if col in sub.columns:
                row[f"mean_{col}"] = round(sub[col].mean(), 2)
        # Extra fields
        for extra in ["optimizer", "use_log", "label", "n_features",
                      "removed", "base_model", "calibration"]:
            if extra in sub.columns:
                row[extra] = sub[extra].iloc[0]
        rows.append(row)
    return pd.DataFrame(rows)

# Wilcoxon vs LR for exp3 calibration
def wilcoxon_vs_lr(records, baseline_id="LR_Raw"):
    df_r = pd.DataFrame(records)
    lr_aurocs = df_r[df_r["model_id"] == baseline_id].sort_values("fold")["auroc"].values
    results = []
    for mid in df_r["model_id"].unique():
        sub = df_r[df_r["model_id"] == mid].sort_values("fold")["auroc"].values
        if mid == baseline_id or len(sub) != len(lr_aurocs):
            results.append(dict(model_id=mid, delta_auroc=0.0, wilcoxon_p=float("nan")))
            continue
        try:
            stat, p = wilcoxon(sub, lr_aurocs)
        except Exception:
            p = float("nan")
        results.append(dict(model_id=mid, delta_auroc=round((sub.mean() - lr_aurocs.mean()) * 100, 4), wilcoxon_p=round(p, 4)))
    return pd.DataFrame(results)

# ═══════════════════════════════════════════════════════════════════════════════
# SAVE CSVs
# ═══════════════════════════════════════════════════════════════════════════════

# Combined fold metrics
all_fold_records = exp1_fold_records + exp2_fold_records + exp3_fold_records
df_folds = pd.DataFrame(all_fold_records)
df_folds.to_csv(os.path.join(RESULTS_DIR, "ann_phase8_fold_metrics.csv"), index=False)
print(f"Saved ann_phase8_fold_metrics.csv ({len(df_folds)} rows)")

# Optimizer comparison summary
df_exp1 = pd.DataFrame(exp1_fold_records)
opt_rows = []
for mid in df_exp1["model_id"].unique():
    sub = df_exp1[df_exp1["model_id"] == mid]
    opt_rows.append(dict(
        model_id=mid,
        optimizer=sub["optimizer"].iloc[0],
        use_log=sub["use_log"].iloc[0],
        auroc_mean=round(sub["auroc"].mean(), 6),
        auroc_std=round(sub["auroc"].std(ddof=1), 6),
        brier_mean=round(sub["brier"].mean(), 6),
        brier_std=round(sub["brier"].std(ddof=1), 6),
        log_loss_mean=round(sub["log_loss"].mean(), 6),
        log_loss_std=round(sub["log_loss"].std(ddof=1), 6),
        sensitivity_mean=round(sub["sensitivity"].mean(), 6),
        specificity_mean=round(sub["specificity"].mean(), 6),
        cal_slope_mean=round(sub["cal_slope"].mean(), 6),
        mean_best_epoch=round(sub["best_epoch"].mean(), 1),
        mean_final_val_loss=round(sub["final_val_loss"].mean(), 6),
    ))
df_opt = pd.DataFrame(opt_rows)
df_opt.to_csv(os.path.join(RESULTS_DIR, "ann_phase8_optimizer_comparison.csv"), index=False)
print(f"Saved ann_phase8_optimizer_comparison.csv ({len(df_opt)} rows)")

# Feature ablation summary
df_exp2 = pd.DataFrame(exp2_fold_records)
abl_rows = []
for mid in df_exp2["model_id"].unique():
    sub = df_exp2[df_exp2["model_id"] == mid]
    abl_rows.append(dict(
        model_id=mid,
        label=sub["label"].iloc[0],
        n_features=sub["n_features"].iloc[0],
        removed=sub["removed"].iloc[0],
        auroc_mean=round(sub["auroc"].mean(), 6),
        auroc_std=round(sub["auroc"].std(ddof=1), 6),
        brier_mean=round(sub["brier"].mean(), 6),
        brier_std=round(sub["brier"].std(ddof=1), 6),
        log_loss_mean=round(sub["log_loss"].mean(), 6),
        log_loss_std=round(sub["log_loss"].std(ddof=1), 6),
        sensitivity_mean=round(sub["sensitivity"].mean(), 6),
        specificity_mean=round(sub["specificity"].mean(), 6),
        cal_slope_mean=round(sub["cal_slope"].mean(), 6),
    ))
df_abl = pd.DataFrame(abl_rows)
df_abl.to_csv(os.path.join(RESULTS_DIR, "ann_phase8_feature_ablation.csv"), index=False)
print(f"Saved ann_phase8_feature_ablation.csv ({len(df_abl)} rows)")

# Calibration summary
df_exp3 = pd.DataFrame(exp3_fold_records)
cal_rows = []
for mid in df_exp3["model_id"].unique():
    sub = df_exp3[df_exp3["model_id"] == mid]
    cal_rows.append(dict(
        model_id=mid,
        base_model=sub["base_model"].iloc[0],
        calibration=sub["calibration"].iloc[0],
        auroc_mean=round(sub["auroc"].mean(), 6),
        auroc_std=round(sub["auroc"].std(ddof=1), 6),
        brier_mean=round(sub["brier"].mean(), 6),
        brier_std=round(sub["brier"].std(ddof=1), 6),
        log_loss_mean=round(sub["log_loss"].mean(), 6),
        log_loss_std=round(sub["log_loss"].std(ddof=1), 6),
        sensitivity_mean=round(sub["sensitivity"].mean(), 6),
        specificity_mean=round(sub["specificity"].mean(), 6),
        cal_slope_mean=round(sub["cal_slope"].mean(), 6),
        cal_intercept_mean=round(sub["cal_intercept"].mean(), 6),
        ece_mean=round(sub["ece"].mean(), 6),
        ece_std=round(sub["ece"].std(ddof=1), 6),
    ))
df_cal = pd.DataFrame(cal_rows)
df_cal.to_csv(os.path.join(RESULTS_DIR, "ann_phase8_calibration_comparison.csv"), index=False)
print(f"Saved ann_phase8_calibration_comparison.csv ({len(df_cal)} rows)")

# ECE bin detail
df_ece = pd.DataFrame(exp3_ece_records)
df_ece.to_csv(os.path.join(RESULTS_DIR, "ann_phase8_ece_bins.csv"), index=False)
print(f"Saved ann_phase8_ece_bins.csv ({len(df_ece)} rows)")

# ═══════════════════════════════════════════════════════════════════════════════
# PRINT FINAL SUMMARIES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*70)
print("EXPERIMENT 1: OPTIMIZER COMPARISON — SUMMARY")
print("="*70)
print(df_opt[["model_id","optimizer","use_log","auroc_mean","auroc_std",
              "brier_mean","log_loss_mean","sensitivity_mean","specificity_mean",
              "cal_slope_mean","mean_best_epoch"]].to_string(index=False))

print("\n\n" + "="*70)
print("EXPERIMENT 2: FEATURE ABLATION — SUMMARY")
print("="*70)
print(df_abl[["model_id","n_features","auroc_mean","auroc_std",
              "brier_mean","log_loss_mean","sensitivity_mean","specificity_mean",
              "cal_slope_mean"]].to_string(index=False))

print("\n\n" + "="*70)
print("EXPERIMENT 3: CALIBRATION — SUMMARY")
print("="*70)
print(df_cal[["model_id","base_model","calibration","auroc_mean","auroc_std",
              "brier_mean","log_loss_mean","cal_slope_mean","ece_mean"]].to_string(index=False))

# Wilcoxon tests
print("\n\n" + "="*70)
print("WILCOXON SIGNED-RANK TESTS (all vs LR_Raw on Exp3 fold AUROCs)")
print("="*70)
wdf = wilcoxon_vs_lr(exp3_fold_records, baseline_id="LR_Raw")
print(wdf.to_string(index=False))

print("\n\nPhase 8 script completed successfully.")
print(f"All results saved to: {RESULTS_DIR}")
