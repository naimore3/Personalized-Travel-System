import requests

class BigModel:
    def __init__(self):
        self.token = "your_big_model_token"
        self.api_url = "your_big_model_api_url"

    def query(self, question):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {
            "question": question
        }
        response = requests.post(self.api_url, headers=headers, json=data)
        return response.json().get('result')
    