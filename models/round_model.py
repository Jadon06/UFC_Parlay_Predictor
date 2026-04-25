from sklearn.metrics import accuracy_score
import xgboost as xgb
from sklearn.model_selection import train_test_split
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import CalibratedClassifierCV
import joblib
import math

letters = 'abcdefgh'
to_concatenate = [pd.read_csv(f"training_data/fighters_{letter}.csv") for letter in letters]
data = pd.concat(to_concatenate, ignore_index=True)
data = data.sort_values("Date", ignore_index=True)

def recompute_elo(data):
    elo = {}
    f_elos = []
    o_elos = []

    for _, row in data.iterrows():
        fighter = row["Fighter"]
        opponent = row["Opponent"]
        winner = row["winner"]

        f_elo = elo.get(fighter, 1000.0)
        o_elo = elo.get(opponent, 1000.0)
        f_elos.append(f_elo)
        o_elos.append(o_elo)

        diff = abs(f_elo - o_elo)
        if diff == 0:
            change = f_elo * 0.008
        elif diff <= 30:
            change = diff
        elif diff <= 100:
            change = math.ceil(diff * 0.7)
        else:
            change = diff * 0.07

        if winner == 1:
            elo[fighter] = f_elo + change
            elo[opponent] = o_elo - change
        elif winner == 0:
            elo[fighter] = f_elo - change
            elo[opponent] = o_elo + change

    data["f_ELO"] = f_elos
    data["o_ELO"] = o_elos
    return data

def recompute_survivor_score(data):
    KO_TKO_MULT = {1: 1.8, 2: 1.3, 3: 1.0, 4: 0.7, 5: 0.2}
    SUB_MULT    = {1: 1.2, 2: 1.2, 3: 0.8, 4: 0.5, 5: 0.1}

    scores = {}
    f_scores = []
    o_scores = []

    for _, row in data.iterrows():
        fighter  = row["Fighter"]
        opponent = row["Opponent"]
        method   = row["method"]
        winner   = row["winner"]
        rnd      = max(1, min(5, int(row["Round"]) if pd.notna(row["Round"]) else 3))

        f_score = scores.get(fighter,  1000.0)
        o_score = scores.get(opponent, 1000.0)
        f_scores.append(f_score)
        o_scores.append(o_score)

        if method == "KO/TKO":
            if winner == 1:
                scores[fighter]  = scores.get(fighter,  1000.0) + rnd * 10
                scores[opponent] = scores.get(opponent, 1000.0) - 100 * KO_TKO_MULT.get(rnd, 1.0)
            elif winner == 0:
                scores[opponent] = scores.get(opponent, 1000.0) + rnd * 10
                scores[fighter]  = scores.get(fighter,  1000.0) - 100 * KO_TKO_MULT.get(rnd, 1.0)
        elif method == "SUB":
            if winner == 1:
                scores[fighter]  = scores.get(fighter,  1000.0) + rnd * 10
                scores[opponent] = scores.get(opponent, 1000.0) - 100 * SUB_MULT.get(rnd, 1.0)
            elif winner == 0:
                scores[opponent] = scores.get(opponent, 1000.0) + rnd * 10
                scores[fighter]  = scores.get(fighter,  1000.0) - 100 * SUB_MULT.get(rnd, 1.0)
        elif method == "DEC":
            scores[fighter]  = scores.get(fighter,  1000.0) + 100
            scores[opponent] = scores.get(opponent, 1000.0) + 100

    data["f_survivor_score"] = f_scores
    data["o_survivor_score"] = o_scores
    return data

data = recompute_elo(data)
data = recompute_survivor_score(data)

drop_cols = ["W/L", "winner", "method", "Date", "Round", "Fighter", "Opponent"]
X = data.drop(columns=drop_cols)

y = data["Round"] - 1

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = XGBClassifier(
    objective="multi:softprob",
    num_class=int(y.nunique()),
    n_estimators=1000,
    max_depth=4,
    learning_rate=0.02,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="mlogloss",
    tree_method="hist",
    random_state=42
)

model.fit(X_train, y_train)

probs = model.predict_proba(X_test)
preds = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, preds)) # Accuracy: 0.4983277591973244
print("Log Loss:", log_loss(y_test, probs, labels=list(range(int(y.nunique()))))) # Log Loss: 1.122685476222893

joblib.dump(model, "trained_models/ufc_round_prediction_model.pkl")
joblib.dump(X_train.columns.tolist(), "features/ufc_round_prediction_features.pkl")