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
    VALID_API_VERSIONS = ['2022-12-01', '2023-05-15']

    def __init__(
            self,
            credentials,
            prompt_load_order,
            use_azure=True,
            api_version='2023-05-15'):
        self.use_azure = use_azure
        if self.use_azure:
            openai.api_key = credentials["azureopenai"]["AZURE_OPENAI_KEY"]
            openai.api_base = credentials["azureopenai"]["AZURE_OPENAI_ENDPOINT"]
            openai.api_type = 'azure'
            if api_version not in self.VALID_API_VERSIONS:
                raise ValueError(
                    f'api_version must be one of {self.VALID_API_VERSIONS}')
            openai.api_version = api_version
        else:
            openai.organization = credentials["openai"]["YOUR_ORG_ID"]
            openai.api_key = credentials["openai"]["OPENAI_API_KEY"]

        self.credentials = credentials
        self.messages = []
        self.max_token_length = 8000
        self.max_completion_length = 2000
        self.last_response = None
        self.query = ''
        self.instruction = ''
        # load prompt file
        fp_system = os.path.join(dir_system, 'system.txt')
        with open(fp_system) as f:
            data = f.read()
        self.system_message = {"role": "system", "content": data}

        # load prompt file
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
        fp_query = os.path.join(dir_query, 'query.txt')
        with open(fp_query) as f:
            self.query = f.read()
    # See
    # https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/chatgpt#chatml

    def create_prompt(self):
        prompt = ""
        if self.use_azure and openai.api_version == '2022-12-01':
            prompt = "<|im_start|>system\n"
            prompt += self.system_message["content"]
            prompt += "\n<|im_end|>\n"
            for message in self.messages:
                prompt += f"\n<|im_start|>{message['sender']}\n{message['text']}\n<|im_end|>"
            prompt += "\n<|im_start|>assistant\n"
            print('prompt length: ' + str(len(enc.encode(prompt))))
            if len(enc.encode(prompt)) > self.max_token_length - \
                    self.max_completion_length:
                print('prompt too long. truncated.')
                # truncate the prompt by removing the oldest two messages
                self.messages = self.messages[2:]
                prompt = self.create_prompt()
        else:
            prompt = []
            prompt.append(self.system_message)
            for message in self.messages:
                prompt.append(
                    {"role": message['sender'], "content": message['text']})
            prompt_content = ""
            for message in prompt:
                prompt_content += message["content"]
            print('prompt length: ' + str(len(enc.encode(prompt_content))))
            if len(enc.encode(prompt_content)) > self.max_token_length - \
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
        if text.startswith('```python'):
            text_json = text[text.find(
                '```python') + len('```python'):text.find('\n```')]
            text_json.replace('```', '')
            return text_json
        if text.find('```') == -1:
            return text
        text_json = text[text.find(
            '```') + 3:text.find('```', text.find('```') + 3)]
        return text_json

    def generate(self, message, environment, is_user_feedback=False):
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

        if self.use_azure and openai.api_version == '2022-12-01':
            # Remove unsafe user inputs. May need further refinement in the
            # future.
            if message.find('<|im_start|>') != -1:
                message = message.replace('<|im_start|>', '')
            if message.find('<|im_end|>') != -1:
                message = message.replace('<|im_end|>', '')
            deployment_name = self.credentials["azureopenai"]["AZURE_OPENAI_DEPLOYMENT_NAME_CHATGPT"]
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
        elif self.use_azure and openai.api_version == '2023-05-15':
            deployment_name = self.credentials["azureopenai"]["AZURE_OPENAI_DEPLOYMENT_NAME_CHATGPT"]
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=self.create_prompt(),
                temperature=0.1,
                max_tokens=self.max_completion_length,
                top_p=0.5,
                frequency_penalty=0.0,
                presence_penalty=0.0)
            text = response['choices'][0]['message']['content']
        else:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                # "gpt-4" is available, too. Check the available models in https://platform.openai.com/docs/models/
                messages=self.create_prompt(),
                temperature=0.1,
                max_tokens=self.max_completion_length,
                top_p=0.5,
                frequency_penalty=0.0,
                presence_penalty=0.0)
            text = response['choices'][0].message.content
        print(text)
        self.last_response = text
        self.last_response = self.extract_json_part(self.last_response)
        self.last_response = self.last_response.replace("'", "\"")
        # dump to a text file
        with open('last_response.txt', 'w') as f:
            f.write(self.last_response)
        try:
            self.json_dict = json.loads(self.last_response, strict=False)
            self.environment = None
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
    # Logic
    # 1. example of manipulation in front of shelf
    if scenario_name == 'shelf':
        environment = {
            "assets": [
                "<table>",
                "<shelf_bottom>",
                "<shelf_top>",
                "<trash_bin>",
                "<floor>"],
            "asset_states": {
                "<shelf_bottom>": "on_something(<table>)",
                "<trash_bin>": "on_something(<floor>)"},
            "objects": [
                "<spam>",
                "<juice>"],
            "object_states": {
                "<spam>": "on_something(<table>)",
                "<juice>": "on_something(<shelf_bottom>)"}}
        instructions = [
            'Take the spam, and throw it away if the our-of-date date is expired. Otherwise, put it on the shelf.']
    else:
        parser.error('Invalid scenario name:' + scenario_name)

    aimodel = ChatGPT(
        credentials,
        prompt_load_order=prompt_load_order,
        use_azure=True,
        api_version='2022-12-01')

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
                # For this example, you need to update the environment on site.
                environment = environment
                break
        aimodel.dump_json(f'./out/{scenario_name}/{i}')
