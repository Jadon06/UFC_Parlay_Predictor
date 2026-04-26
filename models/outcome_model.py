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
# print(data[data["o_ctrl"] != 0.0]["o_ctrl"])

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

data = recompute_elo(data)

data["f_striker_score"] = data["f_SLpM"] * (1-data["f_TD_pct"]) # score the fighters striking ability
data["f_grappler_score"] = data["f_TD_pct"] + data["f_Sub_pct"] # score fighters grappling ability

data["o_striker_score"] = data["o_SLpM"] * (1 - data["o_TD_pct"]) # score opponents striking ability
data["o_grappler_score"] = data["o_TD_pct"] + data["o_Sub_pct"] # score opponents grappling ability

data["striker_vs_striker"] = data["f_striker_score"] + data["o_striker_score"]
data["grappler_vs_grappler"] = data["f_grappler_score"] + data["o_grappler_score"]
data["style_clash"] = abs(data["f_striker_score"] - data["o_grappler_score"])

data["finish_pressure"] = data["f_Finish_pct"] + data["o_Finish_pct"] # higher value -> less likely to go to decision
data["KO_pressure"] = data["f_KO_pct"] + data["o_KO_pct"]
data["SUB_pressure"] = data["f_Sub_pct"] + data["o_Sub_pct"]

data["damage_diff"] = data["f_SLpM"] - data["o_SLpM"]
data["damage_diff_rev"] = data["o_SLpM"] - data["f_SApM"]
data["control_diff"] = data["f_ctrl"] - data["o_ctrl"]

drop_cols = ["method", "winner", "W/L", "Fighter", "Opponent", "Date"]
X = data.drop(columns=drop_cols)

le = LabelEncoder() 
y = le.fit_transform(data["method"]) # encodes each 'method' into a numeric value

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
# Train Model
model = XGBClassifier(
    objective="multi:softprob",
    num_class=len(le.classes_),
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

print("Accuracy:", accuracy_score(y_test, preds)) # Accuracy: 0.6789297658862876
print("Log Loss:", log_loss(y_test, probs)) # Log Loss: 0.7668990628648714

joblib.dump(model, "trained_models/ufc_outcome_model.pkl")
joblib.dump(X_train.columns.tolist(), "features/ufc_outcomes_features.pkl")
joblib.dump(le, "label_encoder.pkl")