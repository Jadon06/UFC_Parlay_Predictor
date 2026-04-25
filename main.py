from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent import encode_image, extract_parlay
from predictions import get_fighter_data

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from agent import ParlayLeg
import joblib

from Data_Extraction_and_Cleaning import FighterInfo

from pydantic import BaseModel
from typing import Literal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ufc-parlay-predictor.vercel.app/"],            # List of allowed origins
    allow_credentials=True,           # Allow cookies/auth headers
    allow_methods=["*"],              # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],              # Allow all request headers
)

class modelReturn(BaseModel):
    model_name: Literal['ufc_outcome_model.pkl', 'ufc_round_prediction_model.pkl', 'ufc_WL_model.pkl']

model = ChatOllama(
    model="qwen3",
    temperature=0,
    max_tokens=1000,
    timeout=30,
).with_structured_output(modelReturn)

system_prompt = """ You are an agent tasked with deciding which machine learning model is best to use for each leg in a parlay.
                A parlay leg is defined by the class ParlayLeg, which has been imported to this file.
                Your options are the following:
                    1. 'ufc_outcome_model.pkl' -> This model is best for predicting the method of victory for a given fight
                    2. 'ufc_round_prediction_model.pkl' -> This model is best for predicting the round the fight ends on which can be from 1-5
                    3. 'ufc_WL_model.pkl' -> This model is best for predicting win loss probability for a given fighter

                """

def load_model(model: str):
    features = {
        "ufc_outcome_model.pkl" : "ufc_outcome_features.pkl",
        "ufc_round_prediction_model.pkl" : "ufc_round_predictions_features.pkl",
        "ufc_WL_model.pkl" : "ufc_WL_features.pkl"
    }
    model = joblib.load(model)
    features = joblib.load(features[model])

    return model, features

"""
probabilities translation:
- 0.50 → coin flip
- 0.60 → slight edge
- 0.70 → strong favorite
- 0.80+ → dominant mismatch
"""

@app.post("/")
async def predict(parlay: str):
    # Extract Data
    extracted_parlay = extract_parlay(parlay)
    parlay_data = get_fighter_data(extracted_parlay)

    # choose and load models
    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Choose the predictive models based on the extracted parlay")
    ])

    # new_fight = new_fight[features]

    # prob = model.predict_proba(new_fight)[0][1]

    # print(prob)
    return

