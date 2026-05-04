import re
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


# Apply normalization (frozen)
def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    text = re.sub(r"([!?])\1{2,}", r"\1\1", text)
    text = re.sub(r"\s+", " ", text)
    return text


def main():

    # Load dataset and keep relevant columns
    df = pd.read_csv("../data/dataset.csv")
    df = df[["text", "label"]].dropna()

    # Text normalization
    df["text"] = df["text"].apply(normalize_text)

    X = df["text"]
    y = df["label"]

    # Split dataset into training (70%) and testing (30%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.30,
        stratify=y,
        random_state=42
    )

    print("Split sizes:")
    print("Train:", len(X_train))
    print("Test :", len(X_test))

    # Feature extraction (TF-IDF, frozen)
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=10000
    )
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # Train SVM on training set
    model = LinearSVC()
    model.fit(X_train_tfidf, y_train)

    # Evaluate model on testing set
    y_pred = model.predict(X_test_tfidf)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)

    print("\nSVM Test Results:")
    print(f"Accuracy : {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall   : {rec:.4f}")
    print(f"F1-score : {f1:.4f}")
    print("Confusion Matrix:\n", cm)

    # Save SVM model and TF-IDF vectorizer
    joblib.dump(model, "../models/svm_model.pkl")
    joblib.dump(vectorizer, "../models/tfidf_vectorizer.pkl")

    print("\nSaved:")
    print(" - models/svm_model.pkl")
    print(" - models/tfidf_vectorizer.pkl")


if __name__ == "__main__":
    main()