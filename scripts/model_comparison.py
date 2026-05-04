import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


# Text normalization function
def normalize_text(text):
    text = text.lower().strip()

    # Reduce excessive repeated characters
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)

    # Reduce excessive repeated punctuations
    text = re.sub(r'([!?])\1{2,}', r'\1\1', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    return text


# Load and prepare dataset
df = pd.read_csv("../data/dataset.csv")

# Keep only relevant columns: text, label
df = df[["text", "label"]]

# Apply text normalization
df["text"] = df["text"].astype(str).apply(normalize_text)

X = df["text"]
y = df["label"]


# Split data into training (70%) and testing (30%)
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.30,
    stratify=y,
    random_state=42
)

print("Dataset split sizes:")
print(f"Train: {len(X_train)}")
print(f"Test : {len(X_test)}")


# Feature extraction (TF-IDF)
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),   # unigrams + bigrams
    max_features=10000
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)


# Define models (LR, SVM, RF)
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Support Vector Machine": LinearSVC(),
    "Random Forest": RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )
}


# Train and evaluate models on testing set
results = {}

print("\nTest Set Results:")
print("-" * 50)

for name, model in models.items():
    model.fit(X_train_tfidf, y_train)
    y_pred = model.predict(X_test_tfidf)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)

    results[name] = {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "cm": cm,
        "model": model
    }

    print(f"{name}")
    print(f"  Accuracy : {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall   : {rec:.4f}")
    print(f"  F1-score : {f1:.4f}")
    print(f"  Confusion Matrix:\n{cm}")
    print()


# Select best model based on F1-score
best_model_name = max(results, key=lambda x: results[x]["f1"])
best_cm = results[best_model_name]["cm"]

# Save best model and vectorizer
joblib.dump(best_model_name, "../best_model.pkl")
joblib.dump(vectorizer, "../tfidf_vectorizer.pkl")

print("Best model and vectorizer saved successfully.")

print(f"Best model selected: {best_model_name}")


# Visualization section

# F1-score comparison
model_names = list(results.keys())
f1_scores = [results[m]["f1"] for m in model_names]

plt.figure(figsize=(8, 5))
plt.bar(model_names, f1_scores)
plt.ylim(0.90, 1.0)
plt.title("Test F1-score Comparison Across Models")
plt.ylabel("F1-score")
plt.xlabel("Model")
plt.show()


# Precision / Recall / F1-score comparison
precision = [results[m]["precision"] for m in model_names]
recall = [results[m]["recall"] for m in model_names]
f1 = [results[m]["f1"] for m in model_names]

x = np.arange(len(model_names))
width = 0.25

plt.figure(figsize=(10, 6))
plt.bar(x - width, precision, width, label="Precision")
plt.bar(x, recall, width, label="Recall")
plt.bar(x + width, f1, width, label="F1-score")

plt.xticks(x, model_names)
plt.ylim(0.90, 1.0)
plt.ylabel("Score")
plt.title("Test Metrics Comparison Across Models")
plt.legend()
plt.show()


# Confusion Matrix
for model_name, result in results.items():
    cm = result["cm"]

    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Predicted Safe", "Predicted Phishing"],
        yticklabels=["Actual Safe", "Actual Phishing"]
    )
    plt.title(f"Confusion Matrix – {model_name} (Test Set)")
    plt.ylabel("Actual Label")
    plt.xlabel("Predicted Label")
    plt.show()
