from sklearn.metrics import accuracy_score
import xgboost as xgb
from sklearn.model_selection import train_test_split
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.calibration import CalibratedClassifierCV
import joblib

from Data_Extraction_and_Cleaning import FighterInfo

""" train w/l model 
    training data rows: 6466
    testing data rows: 2484
"""

import math

letters = 'abcdefgh'
to_concatenate = [pd.read_csv(f"training_data/fighters_{letter}.csv") for letter in letters]
data = pd.concat(to_concatenate, ignore_index=True)
data = data.sort_values("Date", ignore_index=True)
data["winner"] = (data["winner"] == data["Fighter"]).astype(int)

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

print(data.tail())

data = recompute_elo(data)
data["SLpM_diff"] = data["f_SLpM"] - data["o_SLpM"]
data["SApM_diff"] = data["f_SApM"] - data["o_SApM"]
data["TD_diff"]   = data["f_TD_pct"] - data["o_TD_pct"]
data["KO_diff"]   = data["f_KO_pct"] - data["o_KO_pct"]
data["Sub_diff"]  = data["f_Sub_pct"] - data["o_Sub_pct"]
data["Fin_diff"]  = data["f_Finish_pct"] - data["o_Finish_pct"]
data["ELO_diff"] = data["f_ELO"] - data["o_ELO"]

split_date = "2021-01-01"
train = data[data["Date"] <= split_date]
test = data[data["Date"] > split_date]

drop_cols = ["W/L", "winner", "Date", "Fighter", "Opponent"]

train = data[data["Date"] <= split_date]
test = data[data["Date"] > split_date]

X_train = train.drop(columns=drop_cols)
y_train = train["winner"]

X_test = test.drop(columns=drop_cols)
y_test = test["winner"]

scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

# Build Model
model = XGBClassifier(
    n_estimators=800,
    max_depth=4,
    learning_rate=0.02,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    objective="binary:logistic",
    eval_metric="logloss",
    tree_method="hist",
    random_state=42
)
# train model
model.fit(X_train, y_train)

probs = model.predict_proba(X_test)[:, 1]
preds = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, preds))
print("Log Loss:", log_loss(y_test, probs))
print("ROC AUC:", roc_auc_score(y_test, probs))

# joblib.dump(model, "models/ufc_WL_model.pkl")
joblib.dump(X_train.columns.tolist(), "expected_results/ufc_features.pkl")