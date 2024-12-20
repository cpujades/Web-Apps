import os
import requests
from app.core.config import config
from app.schemas.summarize import SummarizeFormat
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter


DEEPGRAM_API_KEY = config.DEEPGRAM_API_KEY

SYSTEM_PROMPT = config.SYSTEM_PROMPT
USER_PROMPT = config.USER_PROMPT

OPENAI_API_KEY = config.OPENAI_API_KEY
GEMINI_API_KEY = config.GEMINI_API_KEY
ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY
GROK_API_KEY = config.GROK_API_KEY

VOYAGEAI_API_KEY = config.VOYAGEAI_API_KEY

voyageai_headers = {
    "Authorization": "Bearer " + VOYAGEAI_API_KEY,
    "content-type": "application/json",
}

voyageai_endpoint = "https://api.voyageai.com/v1/embeddings"


def deepgram_transcription(file_url: str) -> str:
    # Define the URL for the Deepgram API endpoint
    deepgram_endpoint = "https://api.deepgram.com/v1/listen"

    # Define the headers for the HTTP request
    deepgram_headers = {
        "Accept": "application/json",
        "Authorization": "Token " + DEEPGRAM_API_KEY,
        "Content-Type": "application/json",
    }
    # Define the data for the HTTP request
    data = {"url": file_url}

    query_params = {
        "detect_language": "true",
        "model": "nova-2",
        "smart_format": "true",
    }

    # Make the HTTP request
    response = requests.post(
        deepgram_endpoint, headers=deepgram_headers, params=query_params, json=data
    )
    json = response.json()
    transcript = json["results"]["channels"][0]["alternatives"][0]["transcript"]
    return transcript


def summarize_podcast(transcript: str, model: str = "gemini-1.5-flash") -> str:
    if "grok" in model:
        api_key = GROK_API_KEY
        base_url = "https://api.x.ai/v1"
    elif "gemini" in model:
        api_key = GEMINI_API_KEY
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    else:
        api_key = OPENAI_API_KEY
        base_url = "https://api.openai.com/v1"

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.beta.chat.completions.parse(
        model=model,
        max_completion_tokens=900,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"<transcription> {transcript} </transcription>",
            },
        ],
        response_format=SummarizeFormat,
    )

    summary = response.choices[0].message.parsed.summary

    return summary


def create_embeddings(text, input_type):
    voyageai_params = {
        "model": "voyage-3",
        "input_type": input_type,
    }

    if len(text) > 1024:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024, chunk_overlap=20
        )
        chunks = text_splitter.split_text(text)
        voyageai_params["input"] = chunks
    else:
        voyageai_params["input"] = [text]

    voyageai_response = requests.post(
        voyageai_endpoint, headers=voyageai_headers, json=voyageai_params
    )
    voyageai_json = voyageai_response.json()
    embeddings = voyageai_json["data"]

    embeddings_dict = {
        "embeddings": embeddings,
        "text": chunks,
    }

    return embeddings_dict


def answer_user_message(user_question, top_passages, model: str = "gemini-1.5-flash"):
    if "grok" in model:
        api_key = GROK_API_KEY
        base_url = "https://api.x.ai/v1"
    elif "gemini" in model:
        api_key = GEMINI_API_KEY
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    else:
        api_key = OPENAI_API_KEY
        base_url = "https://api.openai.com/v1"

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=2048,
        messages=[
            {
                "role": "system",
                "content": USER_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
                <podcast_passages> {top_passages} </podcast_passages>
                <user_question> {user_question} </user_question>
                """,
            },
        ],
    )

    answer = response.choices[0].message.content

    return answer
