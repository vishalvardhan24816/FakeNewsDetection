import json
import requests
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

class subjective:
    def __init__(self):
        self.model = AutoModelForSequenceClassification.from_pretrained('lighteternal')
        self.tokenizer = AutoTokenizer.from_pretrained('lighteternal')

    def send_request(self, text):
        inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors='pt')

        with torch.no_grad():
            outputs = self.model(**inputs)

        predicted_label = torch.argmax(outputs.logits).item()
        print(predicted_label)

        if predicted_label == 0:
            return "subjective"

        else:
            return "objective"
