from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.ml_classifier import normalize_text


# Resolve project root safely for local + Render deployment
BASE_DIR = Path(__file__).resolve().parent.parent

# Load dataset for RAG retrieval
DATASET_PATH = BASE_DIR / "data" / "dataset.csv"

df = pd.read_csv(DATASET_PATH)

# Keep only required columns: text, label
df = df[["text", "label"]].dropna()

# Normalize dataset text using the same preprocessing functions
df["clean_text"] = df["text"].astype(str).apply(normalize_text)


# Create TF-IDF vectorizer for retrieval
retrieval_vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=10000
)

dataset_vectors = retrieval_vectorizer.fit_transform(df["clean_text"])


# Retrieve similar examples from the dataset
def retrieve_similar_examples(
        
        # New incoming message
        message_text: str,
        
        # Number of similar examples to retrieve: 3
        top_k: int = 3,
        
        # Label filter: 1 = phishing examples, 0 = safe examples, none = all examples
        label_filter=None
) -> list[dict]:
    cleaned_message = normalize_text(message_text)

    message_vector = retrieval_vectorizer.transform([cleaned_message])
    similarity_scores = cosine_similarity(message_vector, dataset_vectors).flatten()

    temp_df = df.copy()
    temp_df["similarity"] = similarity_scores

    if label_filter is not None:
        temp_df = temp_df[temp_df["label"] == label_filter]

    top_examples = temp_df.sort_values(by="similarity", ascending=False).head(top_k)

    results = []
    
    
    # Display list of dictionaries containing text, label and similarity score
    for _, row in top_examples.iterrows():
        results.append({
            "text": row["text"],
            "label": int(row["label"]),
            "similarity": round(float(row["similarity"]), 4)
        })

    return results
