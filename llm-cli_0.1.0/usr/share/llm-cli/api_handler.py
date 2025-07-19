# Dependencies 
import requests as rq

# This program will handle the API calls used in the subsystem

class APIHandler: 
    def __init__(self, url: str, headers: dict): 
        self.url = url
        self.headers = headers 


    
    def send_request(self, model_parameters: dict): 

        # send post
        response = rq.post(url=self.url, headers=self.headers, json=model_parameters)
        print(response.json())
        if response.status_code == 200: 
            return response.json()
        else:
            return f"api send request error, this could indicate bad input or a server error. Status code: {response.status_code}"
    


        


