import random
import json
import base64
import os
import time
class Agent:
    def __init__(self, api_handler: object, functions_handler: object = None, system_message: str = "", agent_identifier: str = f"AgentID:{random.randrange(0, 1000000)}"):
        self.agent_identifier = agent_identifier
        self.api_handler = api_handler
        self.system_message = system_message
        self.messages = [{"role": "system", "content": self.system_message}]
        self.functions = functions_handler

        self.tool_recursions = {"current": 0, "max": 20}  # Added max recursions
        self.audio_player = AudioPlayback()
        self.modality = 'text'
        

    def get_identifier(self): 
        return self.agent_identifier
    
    def clear_messages(self): 
        self.messages = [{"role": "system", "content": self.system_message}]
        self.modality = 'text'

    def chat(self, input_data: list=None):
        
        # print(input_data)  # For debugging
        if input_data:
            self.messages.append({"role": "user", "content": input_data})

        self.model_parameters = {'model': 'o3-mini', 'messages': self.messages, "max_completion_tokens": 8096}
        
        
        if input_data and any([item['type'] == 'input_audio' for item in input_data]) or self.modality == 'audio':
            print("Audio input detected")
            self.modality = 'audio' 
            self.model_parameters['model'] = "gpt-4o-audio-preview"
            self.model_parameters['audio'] = {'voice': 'alloy', 'format': 'wav'}
            self.model_parameters['modalities'] = ['text']
        
        
        if self.functions: 
            self.model_parameters['tools'] = self.functions.get_tools()
            self.model_parameters['tool_choice'] = 'auto'


        model_response = self.api_handler.send_request(self.model_parameters)

        #print(model_response)

        if not model_response or "error" in model_response:
            time.sleep(1)
            model_response = self.api_handler.send_request(self.model_parameters)

        if model_response and 'choices' in model_response and model_response['choices'][0]['message']:
            response_message = model_response['choices'][0]['message']

    
            if 'audio' in model_response:
                audio_data = model_response['audio']['data']
                self.audio_player.play_audio(audio_data)
            
            self.messages.append(response_message)

            if 'tool_calls' in response_message:
                if self.tool_recursions['current'] < self.tool_recursions['max']:
                    self.tool_recursions['current'] += 1
                    for tool_call in response_message['tool_calls']:
                        function_name = tool_call['function']['name']
                        function_arguments = json.loads(tool_call['function']['arguments'])

                        tool_output = self.functions.run_tool(function_name, function_arguments)
                        print(f"tool_call: {function_name} with inputs {str(function_arguments)}\ntool output: {tool_output}")
                        self._add_message(content=json.dumps(tool_output), call_id=tool_call['id'])
                    return self.chat()
                
                self.tool_recursions['current'] = 0
                message = response_message["content"]
                self._add_message(content=message)
                return message
            else:
                self.tool_recursions['current'] = 0
                message = response_message["content"]
                self._add_message(content=message)
                return message
        else:
            return "Response is of NoneType or invalid format"

    def _prepare_content(self, message: str, image_path: str = None, audio_data = None):
        content = [{"type": "text", "text": message}]
        if image_path:
            base64_image = self._encode_image(image_path)
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
        if audio_data:
            content.append({
                "type": "input_audio",
                "input_audio": {
                    "data": self._encode_audio(audio_data.read()),
                    "format": "wav"
                }
            })
        
        return content

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_image
        
    def _encode_audio(self, audio_bytes):
        return base64.b64encode(audio_bytes).decode('utf-8')

    def _add_message(self, content, call_id: str = None, image=False, audio=False) -> None:
        """
        Adds a message to the chat history, automatically determining the role.
        """
        

        
        if not self.messages:
            role = "user"
        elif image or audio:  
            role = "user"
        elif call_id or 'tool_calls' in self.messages[-1]:
            role = 'tool'
        elif isinstance(content, dict): 
            #print(f"\n\nCONTENT: {content}: \n\n")
            self.messages.append(content)
            return
        elif self.messages[-1]['role'] in ['system', 'assistant']:
            role = 'user'
        elif self.messages[-1]['role'] in ['user', 'tool']:
            role = 'assistant'
            

        # Validate message roles according to chat rules
        if role == 'system' and len(self.messages) > 0:
            raise ValueError('System message can only be the first message')
        if role == 'tool' and self.messages[-1]['role'] != 'assistant' and self.messages[-1]['role'] != 'tool':
            raise ValueError('Tool message can only follow an assistant message or another tool message')
        if role == 'assistant' and self.messages[-1]['role'] == 'assistant':
            raise ValueError('Assistant message cannot follow another assistant message')

        # Append the new message to the chat history, including optional call_id for tool messages
        message = {'role': role, 'content': content}
        
        if call_id:
            
            message['tool_call_id'] = call_id
        self.messages.append(message)
        

    def remove_image_from_messages(self, filename):
        for message in self.messages:
            if message['role'] == 'user' and isinstance(message['content'], list):
                message['content'] = [item for item in message['content'] if not (item['type'] == 'image_url' and filename in item['image_url']['url'])]
