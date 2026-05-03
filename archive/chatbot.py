import os
from questionanswer import questions, answers, questions_embeddings
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import requests


class chatBot:
    def __init__(self):
        self.received_answer = ""
        self.received_question = ""
        self.API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/distilbert-base-nli-mean-tokens"
        self.headers = {"Authorization": f"Bearer {os.environ.get('HUGGINGFACE_API_TOKEN', '')}"}


    def calculate_sentence_similarity(self, sentence1):
        model = SentenceTransformer("../basenlimean")
        sentence1 = sentence1.replace("?", "")
        print(sentence1)
        exclude = '[!\#\$%\&\(\)\*\+,\."/:;<=>\?@\[\^_`\{\|\}\~]'
        sentence_embeddings = model.encode(
            [
                sentence1.translate(str.maketrans("", "", exclude)).lower(),
            ]
        )
        return sentence_embeddings[0]

    def query(self, payload):
        response = requests.post(self.API_URL, headers=self.headers, json=payload)
        return response.json()


