import openai
import tiktoken
import json
import os
import re
import argparse

enc = tiktoken.get_encoding("cl100k_base")
with open('../../secrets.json') as f:
    credentials = json.load(f)

dir_system = './system'
dir_prompt = './prompt'
dir_query = './query'
prompt_load_order = ['prompt_role',
                     'prompt_function',
                     'prompt_environment',
                     'prompt_output_format',
                     'prompt_example']


class ChatGPT:
    def __init__(self, credentials, prompt_load_order):
        openai.api_key = credentials["chatengine"]["AZURE_OPENAI_KEY"]
        openai.api_base = credentials["chatengine"]["AZURE_OPENAI_ENDPOINT"]
        openai.api_type = 'azure'
        openai.api_version = '2022-12-01'
        self.credentials = credentials
        self.messages = []
        self.max_token_length = 8000
        self.max_completion_length = 2000
        self.last_response = None
        self.query = ''
        self.instruction = ''
        # load prompt file
        self.system_message = "<|im_start|>system\n"
        fp_system = os.path.join(dir_system, 'system.txt')
        with open(fp_system) as f:
            data = f.read()
        self.system_message += data
        self.system_message += "\n<|im_end|>\n"

        # load prompt file
        self.system_prompt = ""
        for prompt_name in prompt_load_order:
            fp_prompt = os.path.join(dir_prompt, prompt_name + '.txt')
            with open(fp_prompt) as f:
                data = f.read()
            data_spilit = re.split(r'\[user\]\n|\[assistant\]\n', data)
            data_spilit = [item for item in data_spilit if len(item) != 0]
            # it start with user and ends with system
            assert len(data_spilit) % 2 == 0
            for i, item in enumerate(data_spilit):
                if i % 2 == 0:
                    self.messages.append({"sender": "user", "text": item})
                else:
                    self.messages.append({"sender": "assistant", "text": item})
        for message in self.messages:
            self.system_prompt += f"\n<|im_start|>{message['sender']}\n{message['text']}\n<|im_end|>"
        self.messages = []
        fp_query = os.path.join(dir_query, 'query.txt')
        with open(fp_query) as f:
            self.query = f.read()

    # See
    # https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/chatgpt#chatml
    def create_prompt(self):
        prompt = self.system_message
        prompt += self.system_prompt
        for message in self.messages:
            prompt += f"\n<|im_start|>{message['sender']}\n{message['text']}\n<|im_end|>"
        prompt += "\n<|im_start|>assistant\n"
        if len(enc.encode(prompt)) > self.max_token_length - \
                self.max_completion_length:
            print('prompt too long. truncated.')
            # truncate the prompt by removing the oldest two messages
            self.messages = self.messages[2:]
            prompt = self.create_prompt()
        return prompt

    def extract_json_part(self, text):
        # because the json part is in the middle of the text, we need to extract it.
        # json part is between ``` and ```.
        # skip if there is no json part
        if text.find('```') == -1:
            return text
        text_json = text[text.find(
            '```') + 3:text.find('```', text.find('```') + 3)]
        return text_json

    def generate(self, message, environment, is_user_feedback=False):
        deployment_name = self.credentials["chatengine"]["AZURE_OPENAI_DEPLOYMENT_NAME_CHATGPT"]
        # Remove unsafe user inputs. May need further refinement in the future.
        if message.find('<|im_start|>') != -1:
            message = message.replace('<|im_start|>', '')
        if message.find('<|im_end|>') != -1:
            message = message.replace('<|im_end|>', '')

        if is_user_feedback:
            self.messages.append({'sender': 'user',
                                  'text': message + "\n" + self.instruction})
        else:
            text_base = self.query
            if text_base.find('[ENVIRONMENT]') != -1:
                text_base = text_base.replace(
                    '[ENVIRONMENT]', json.dumps(environment))
            if text_base.find('[INSTRUCTION]') != -1:
                text_base = text_base.replace('[INSTRUCTION]', message)
                self.instruction = text_base
            self.messages.append({'sender': 'user', 'text': text_base})

        response = openai.Completion.create(
            engine=deployment_name,
            prompt=self.create_prompt(),
            temperature=0.1,
            max_tokens=self.max_completion_length,
            top_p=0.5,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["<|im_end|>"])
        text = response['choices'][0]['text']
        print(text)
        self.last_response = text
        self.last_response = self.extract_json_part(self.last_response)
        self.last_response = self.last_response.replace("'", "\"")
        # dump to a text file
        with open('last_response.txt', 'w') as f:
            f.write(self.last_response)
        try:
            self.json_dict = json.loads(self.last_response, strict=False)
            self.environment = self.json_dict["environment_after"]
        except BaseException:
            self.json_dict = None
            import pdb
            pdb.set_trace()

        if len(self.messages) > 0 and self.last_response is not None:
            self.messages.append(
                {"sender": "assistant", "text": self.last_response})

        return self.json_dict

    def dump_json(self, dump_name=None):
        if dump_name is not None:
            # dump the dictionary to json file dump 1, 2, ...
            fp = os.path.join(dump_name + '.json')
            with open(fp, 'w') as f:
                json.dump(self.json_dict, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--scenario',
        type=str,
        required=True,
        help='scenario name (see the code for details)')
    args = parser.parse_args()
    scenario_name = args.scenario
    # Dual arm manipulation
    # 1. example of manipulation in front of fridge
    if scenario_name == 'fridge':
        environment = {
            "assets": [
                "<fridge>",
                "<floor>"],
            "asset_states": {
                "<fridge>": "on_something(<floor>)"},
            "objects": [
                "<fridge_handle>",
                "<juice>"],
            "object_states": {
                "<fridge_handle>": "closed()",
                "<juice>": "inside_something(<fridge>)"}}
        instructions = [
            'Open the fridge with the right arm, take the juice and put it on the floor with the left arm, and close the fridge',
        ]
    else:
        parser.error('Invalid scenario name:' + scenario_name)

    aimodel = ChatGPT(credentials, prompt_load_order=prompt_load_order)

    if not os.path.exists('./out/' + scenario_name):
        os.makedirs('./out/' + scenario_name)
    for i, instruction in enumerate(instructions):
        print(json.dumps(environment))
        text = aimodel.generate(
            instruction,
            environment,
            is_user_feedback=False)
        while True:
            user_feedback = input(
                'user feedback (return empty if satisfied): ')
            if user_feedback == 'q':
                exit()
            if user_feedback != '':
                text = aimodel.generate(
                    user_feedback, environment, is_user_feedback=True)
            else:
                # update the current environment
                environment = aimodel.environment
                break
        aimodel.dump_json(f'./out/{scenario_name}/{i}')
