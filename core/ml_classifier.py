import re
from pathlib import Path

import joblib


# Resolve project root safely for local + Render deployment
BASE_DIR = Path(__file__).resolve().parent.parent

# Load the trained SVM model and TF-IDF vectorizer from the models folder
MODEL_PATH = BASE_DIR / "models" / "svm_model.pkl"
VECTORIZER_PATH = BASE_DIR / "models" / "tfidf_vectorizer.pkl"

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)


# Normalize incoming message text before classification
def normalize_text(text: str) -> str:
    # Convert text to lowercase
    text = str(text).lower().strip()

    # Reduce excessive repeated characters
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)

    # Reduce excessive repeated punctuation
    text = re.sub(r"([!?])\1{2,}", r"\1\1", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text


# Predict whether a message is safe or phishing/scam
def predict_label(message_text: str) -> int:
    # Normalize raw message text
    cleaned = normalize_text(message_text)

    # If message is too short, treat it as safe
    if len(cleaned) < 3:
        return 0

    # Convert the text into TF-IDF features
    features = vectorizer.transform([cleaned])

    # Use the trained SVM model to classify the message
    prediction = model.predict(features)[0]

    # Prediction output: 0 = safe, 1 = phishing/scam
    return int(prediction)
