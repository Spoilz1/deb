
import os

class Configurations:
    def __init__(self):
        self.API_KEY = "6bTokUckgdMOT5IFPXFcwVgNGrpMej1Zhntl9X6iy3yORP8cZtIiJQQJ99BFACHYHv6XJ3w3AAAAACOGjQfS" 
        if not self.API_KEY:
            raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.headers = {
            "chat": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            }
        }
        self.base_url = "https://api.openai.com/v1"  
        self.endpoints = {
            "URL": "https://api.openai.com",
            "chat": "https://tsachs2-2331-resource.cognitiveservices.azure.com/openai/deployments/o3-mini/chat/completions?api-version=2025-01-01-preview",  
        }

    def get_api_key(self):
        return self.API_KEY

    def get_header(self, service):
        return self.headers.get(service, None)

    def get_endpoint(self, service):
        return self.endpoints.get(service, None)

    def update_api_key(self, new_key):
        self.API_KEY = new_key
        # Update the Authorization header with the new key
        self.headers["chat"]["Authorization"] = f"Bearer {self.API_KEY}"

    def update_endpoint(self, service, new_url):
        if service in self.endpoints:
            self.endpoints[service] = new_url

    def update_header(self, service, key, value):
        if service in self.headers:
            self.headers[service][key] = value
