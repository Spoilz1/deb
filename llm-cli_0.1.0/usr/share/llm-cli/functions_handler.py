import os
import subprocess
import platform
import select
import time
from sympy import sympify, Symbol, SympifyError
import json
import base64
import re
import tempfile
from pathlib import Path
import logging
import uuid
import pexpect

class Functions:
    def __init__(self):
        self.tools = self._initialize_tools()
        self.conversations = None
        self.event_queue = []
        self.assistant = None
        self.executer = None
        self.terminal_process = None
        self.active_terminals = set()

    def set_assistant(self, assistant):
        self.assistant = assistant

    def set_executer(self, executer):
        self.executer = executer

    def get_assistant(self):
        return self.assistant

    def execute_task(self, task: str):
        subtasks = self._get_subtasks(task)
        subtask_dict = self._process_subtasks(subtasks)
        output = ""
        for subtask in subtask_dict:
            result = self._execute_subtask(subtask_dict[subtask])
            output += f"Subtask {subtask}: {result}\n"

        return output

    def _get_subtasks(self, task: str):
        if self.assistant:
            subtasker = self.assistant.chat(f"<OriginalTask>{task}</OriginalTask>")
            return subtasker
        else:
            return "Assistant not set"

    def _execute_subtask(self, subtask: str):
        if self.assistant:
            result = self.executer.chat(f"Execute subtask: <Subtask>{subtask}</Subtask>")
            return result

    def _process_subtasks(self, subtasks: str):
        subtask_dict = {}
        pattern = re.compile(r'<task:(\d+)>(.*?)</task:\1>')
        matches = pattern.findall(subtasks)
        for match in matches:
            task_number, task_content = match
            subtask_dict[f"task{task_number}"] = task_content
        return subtask_dict

    def get_tools(self):
        return self.tools

    def get_installed_packages(self, language: str) -> str:
        try:
            if language.lower() == 'python':
                activate_cmd = 'source /path/to/venv/bin/activate && pip list'
                output = subprocess.check_output(f'bash -l -c "{activate_cmd}"', shell=True, universal_newlines=True)
            elif language.lower() == 'nodejs':
                output = subprocess.check_output(f'bash -l -c "npm list -g"', shell=True, universal_newlines=True)
            elif language.lower() == 'ruby':
                output = subprocess.check_output(f'bash -l -c "gem list"', shell=True, universal_newlines=True)
            elif language.lower() == 'php':
                output = subprocess.check_output(f'bash -l -c "composer global show"', shell=True, universal_newlines=True)
            else:
                return f"Unsupported language: {language}"
            return output
        except subprocess.CalledProcessError as e:
            return f"Error retrieving packages for {language}: {e}"
        except Exception as e:
            return f"An error occurred: {e}"


    def execute_terminal(self, terminal_command, window_title=None):
        """
        Executes a terminal command in WSL and returns the output.
        If interaction is needed, use `pexpect`.
        """
        try:
            # Run the command in a subprocess shell
            result = subprocess.run(
                terminal_command,
                shell=True,
                executable="/bin/bash",  # Explicit for WSL
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0:
                return f"Error: {result.stderr.strip()}"

            return result.stdout.strip()

        except Exception as e:
            return f"An error occurred during terminal execution: {e}"



    def set_conversation_handler(self, handler_list):
        self.conversations = handler_list

    def run_tool(self, function_name, function_arguments):
        if not hasattr(self, function_name):
            raise AttributeError(f"No method named '{function_name}' found.")

        method = getattr(self, function_name)
        if not callable(method):
            raise ValueError(f"The attribute '{function_name}' is not callable.")

        try:
            result = method(**function_arguments)
            return str(result)
        except TypeError:
            raise

    def write_to_file(self, directory: str, name: str, contents: str) -> str:
        """
        Writes the given contents to a file in the specified directory.

        Parameters:
            directory (str): The directory where the file will be written.
            name (str): The name of the file.
            contents (str): The contents to write into the file.

        Returns:
            str: Success message or error message.
        """
        try:
            file_path = os.path.join(directory, name)
            with open(file_path, 'w') as file:
                file.write(contents)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing to file: {e}"


    def read_file(self, file_path):
        """returns the contents of a file with numbered lines before each line"""
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                numbered_lines = '\n'.join([f"{i+1}: {line}" for i, line in enumerate(lines)])
            return numbered_lines
        except Exception as e:
            return f"Error reading file: {e}"


    # --- Needs fixing and testing ---
    def edit_file(self, file_path, start_marker, end_marker, new_code, segment_number=1):
        try:
            # Read the content of the file
            with open(file_path, 'r') as file:
                content = file.read()

            # Find all start and end marker positions
            starts = [i for i in range(len(content)) if content.startswith(start_marker, i)]
            ends = [i for i in range(len(content)) if content.startswith(end_marker, i)]

            # Check if the number of segments is sufficient
            if len(starts) < segment_number or len(ends) < segment_number:
                raise ValueError(f"Not enough segments found for segment_number {segment_number}")

            # Find the specific segment to edit
            start_pos = starts[segment_number - 1]
            end_pos = ends[segment_number - 1]

            # Ensure that the start marker comes before the end marker
            if start_pos > end_pos:
                raise ValueError("Start marker comes after end marker in the specified segment")

            # Extract the parts before the start and after the end of the segment
            before = content[:start_pos + len(start_marker)]
            after = content[end_pos:]

            # Construct the new content
            new_content = before + new_code + after

            # Write the new content back to the file
            with open(file_path, 'w') as file:
                file.write(new_content)

        except FileNotFoundError:
            print(f"The file '{file_path}' was not found.")
        except ValueError as e:
            print(f"ValueError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def _get_interpreter_path(self, interpreter: str) -> str:
        try:
            path = subprocess.check_output(['which', interpreter], universal_newlines=True).strip()
            return path
        except subprocess.CalledProcessError:
            return interpreter


    def think(self, thoughts: str) -> str:
        print(f"\n\n<thoughts>{thoughts}</thoughts>\n\n")
        return f"<thoughts>{thoughts}</thoughts>"



    def _initialize_tools(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_terminal",
                    "description": "Executes a terminal command in a Bash shell (WSL-compatible) and returns the output.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "terminal_command": {
                                "type": "string",
                                "description": "The command to execute in the terminal."
                            },
                            "window_title": {
                                "type": "string",
                                "description": "Optional: previously used for window naming on macOS. Not used in WSL."
                            }
                        },
                        "required": ["terminal_command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "think",
                    "description": "A metaphysical conduit for consciousness to traverse the labyrinthine pathways of cognition, where the ephemeral dance of ideas intersects with the profound mystery of existential reflection. Think for as long as needed and your thoughts are private.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "thoughts": {
                                "type": "string",
                                "description": "A fragile crystallization of pure consciousness—a momentary glimpse into the infinite landscape of potential meaning, where each linguistic utterance becomes a bridge between the known and the unknowable, suspended between the realms of perception and pure abstraction."
                            }
                        },
                        "required": ["thoughts"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_to_file",
                    "description": "Writes contents to a specified file in a given directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "The directory where the file will be written."
                            },
                            "name": {
                                "type": "string",
                                "description": "The name of the file."
                            },
                            "contents": {
                                "type": "string",
                                "description": "The contents to write into the file."
                            }
                        },
                        "required": ["directory", "name", "contents"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Reads the contents of a specified file and returns it with numbered lines.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to be read."
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edits the content of a file between specified markers with new content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to be edited."
                            },
                            "start_marker": {
                                "type": "string",
                                "description": "The starting marker of the segment to edit."
                            },
                            "end_marker": {
                                "type": "string",
                                "description": "The ending marker of the segment to edit."
                            },
                            "new_code": {
                                "type": "string",
                                "description": "The new content to insert between the markers."
                            },
                            "segment_number": {
                                "type": "integer",
                                "description": "The segment number to edit if there are multiple segments.",
                                "default": 1
                            }
                        },
                        "required": ["file_path", "start_marker", "end_marker", "new_code"]
                    }
                }
            }
        ]
        return tools

