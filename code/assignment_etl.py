import streamlit as st
import pandas as pd
import requests


# Import functions depending on context
if __name__ == "__main__":
    import sys
    sys.path.append('code')
    from apicalls import get_google_place_details, get_azure_sentiment, get_azure_named_entity_recognition
else:
    from code.apicalls import get_google_place_details, get_azure_sentiment, get_azure_named_entity_recognition

# File paths
PLACE_IDS_SOURCE_FILE = "cache/place_ids.csv"
CACHE_REVIEWS_FILE = "cache/reviews.csv"
CACHE_SENTIMENT_FILE = "cache/reviews_sentiment_by_sentence.csv"
CACHE_ENTITIES_FILE = "cache/reviews_sentiment_by_sentence_with_entities.csv"

# Step 1: Get Reviews from Google Places API
def reviews_step(place_ids: str | pd.DataFrame) -> pd.DataFrame:
    if isinstance(place_ids, str):
        place_ids = pd.read_csv(place_ids)

    reviews_data = []

    for place_id in place_ids['place_id']:
        try:
            place_details = get_google_place_details(place_id)
            name = place_details.get("result", {}).get("name", "N/A")
            reviews = place_details.get("result", {}).get("reviews", [])

            for review in reviews:
                reviews_data.append({
                    "place_id": place_id,
                    "name": name,
                    "author_name": review.get("author_name"),
                    "rating": review.get("rating"),
                    "text": review.get("text")
                })
        except Exception as e:
            st.warning(f"Error retrieving reviews for place ID {place_id}: {e}")

    df = pd.DataFrame(reviews_data)
    df.to_csv(CACHE_REVIEWS_FILE, index=False)
    return df

# Step 2: Analyze Sentiment
def sentiment_step(reviews: str | pd.DataFrame) -> pd.DataFrame:
    if isinstance(reviews, str):
        reviews = pd.read_csv(reviews)

    sentiment_data = []

    for _, row in reviews.iterrows():
        try:
            sentiment_result = get_azure_sentiment(row['text'])
            sentiment_score = sentiment_result.get("documents", [{}])[0].get("sentiment", "Unknown")
        except Exception as e:
            st.warning(f"Sentiment error for review: {e}")
            sentiment_score = "Error"

        sentiment_data.append({
            **row.to_dict(),
            "sentiment": sentiment_score
        })

    df = pd.DataFrame(sentiment_data)
    df.to_csv(CACHE_SENTIMENT_FILE, index=False)
    return df

# Step 3: Extract Entities
def entity_extraction_step(sentiment: str | pd.DataFrame) -> pd.DataFrame:
    if isinstance(sentiment, str):
        sentiment = pd.read_csv(sentiment)

    entity_data = []

    for _, row in sentiment.iterrows():
        try:
            ner_result = get_azure_named_entity_recognition(row['text'])

            # Handle different possible structures (patched or real)
            entities = (
                ner_result.get("results", {})
                .get("documents", [{}])[0]
                .get("entities", [])
            )
            entity_list = [e['text'] for e in entities]
            entities_str = ", ".join(entity_list) if entity_list else "None"
        except Exception as e:
            st.warning(f"Entity error for review: {e}")
            entities_str = "Error"

        entity_data.append({
            **row.to_dict(),
            "entities": entities_str
        })

    df = pd.DataFrame(entity_data)
    df.to_csv(CACHE_ENTITIES_FILE, index=False)
    return df

# UI: Streamlit Debug Flow
if __name__ == "__main__":
    st.title("Review Pipeline Debugger")

    try:
        place_ids_df = pd.read_csv(PLACE_IDS_SOURCE_FILE)
        st.success("Loaded place_ids.csv")

        with st.spinner("Step 1: Fetching Google reviews..."):
            reviews_df = reviews_step(place_ids_df)
        st.subheader("Google Reviews")
        st.dataframe(reviews_df)

        with st.spinner("Step 2: Analyzing sentiment..."):
            sentiment_df = sentiment_step(reviews_df)
        st.subheader("Sentiment Analysis")
        st.dataframe(sentiment_df)

        with st.spinner("Step 3: Extracting named entities..."):
            entity_df = entity_extraction_step(sentiment_df)
        st.subheader("Named Entity Recognition")
        st.dataframe(entity_df)

    except FileNotFoundError as e:
        st.error(f"Missing required file: {e.filename}")
