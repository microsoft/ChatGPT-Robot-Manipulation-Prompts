import json
import openai
import tiktoken
import json
import os
import re
import time
from virtualhome.simulation.unity_simulator.comm_unity import UnityCommunication

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


def reset(comm, scene_index=None):
    response = comm.post_command({'id': str(time.time()), 'action': 'reset', 'intParams': [
    ] if scene_index is None else [scene_index]})
    return response['success']


def generate_script(input_array):
    output_array = []
    for action in input_array:

        action = action.replace(">", "").replace("<", "").replace(" ", "")
        # Split the action into its constituent parts
        parts = action.split('(')
        verb = parts[0].lower()
        arguments = parts[1].strip(')')
        # Check if there are any objects
        if len(arguments) == 0:
            objects = []
        else:
            objects = arguments.split(',')
            objects = [obj.split('_') for obj in objects]
        # Create the output string
        if len(objects) == 0:
            output_array.append('<char0> [{}]'.format(verb))
        elif len(objects) == 1:
            obj_type, obj_id = objects[0]
            output_array.append(
                '<char0> [{}] <{}> ({})'.format(
                    verb, obj_type, obj_id))
        else:
            obj1_type, obj1_id = objects[0]
            obj2_type, obj2_id = objects[1]
            output_array.append(
                '<char0> [{}] <{}> ({}) <{}> ({})'.format(
                    verb, obj1_type, obj1_id, obj2_type, obj2_id))

    return output_array


def remove_brackets(name):
    return name.replace('<', '').replace('>', '')


def which_room(graph, node_id):
    # Create a mapping from each node ID to its corresponding node data
    id_to_node = {node['id']: node for node in graph['nodes']}
    # Create a mapping from child node ID to its parent node ID
    child_to_parent = {}
    for edge in graph['edges']:
        if edge['from_id'] in child_to_parent.keys():
            child_to_parent[edge['from_id']].append(
                (edge['to_id'], edge['relation_type']))
        else:
            child_to_parent[edge['from_id']] = [
                (edge['to_id'], edge['relation_type'])]
    if node_id not in child_to_parent.keys():
        return None
    # Find the parent node ID(s) of the input node
    parent_node_ids = child_to_parent[node_id]
    # Iterate over all parent node IDs
    for parent_node_id in parent_node_ids:
        # Check if the parent node is a room
        if 'Rooms' in id_to_node[parent_node_id[0]]['category']:
            # Return the name of the room
            return id_to_node[parent_node_id[0]]['class_name']
    # If no room is found, return None
    return None


def find_parent_node(graph, node_name, room_name):
    # Create a mapping from each node ID to its corresponding node data
    id_to_node = {node['id']: node for node in graph['nodes']}
    name_to_id = {}
    for node in graph['nodes']:
        if node['class_name'] in name_to_id.keys():
            name_to_id[node['class_name']].append(node['id'])
        else:
            name_to_id[node['class_name']] = [node['id']]
    child_to_parent = {}
    for edge in graph['edges']:
        if edge['from_id'] in child_to_parent.keys():
            child_to_parent[edge['from_id']].append(
                (edge['to_id'], edge['relation_type']))
        else:
            child_to_parent[edge['from_id']] = [
                (edge['to_id'], edge['relation_type'])]
    if '_' in node_name:
        node_ids = [int(node_name.split('_')[1])]
        node_name = node_name.split('_')[0]
    else:
        # Find the node ID of the input node name
        if node_name not in name_to_id.keys():
            return None
        node_ids = name_to_id[node_name]
        # print(node_ids)
        node_ids = [
            node_id for node_id in node_ids if which_room(
                graph, node_id) == room_name]
        # print(node_ids)
    return_dict = {"object_states": {}, "asset_states": {}}
    for node_id in node_ids:
        if 'GRABBABLE' in id_to_node[node_id]['properties']:
            key_to_add = "object_states"
        else:
            key_to_add = "asset_states"
        # Find the parent node ID(s) of the input node
        if node_id not in child_to_parent.keys():
            return None
        else:
            parent_node_ids = child_to_parent[node_id]

        # Iterate over all parent node IDs
        for parent_node_id in parent_node_ids:
            parent_node = id_to_node[parent_node_id[0]]
            relation_type = parent_node_id[1]
            # focus only in and on
            if relation_type != 'INSIDE' and relation_type != 'ON':
                continue
            if 'Decor' in parent_node['category']:
                continue
            #print(parent_node['class_name'], parent_node_id[1])
            if "<{}_{}>".format(node_name,
                                node_id) in return_dict[key_to_add].keys():
                return_dict[key_to_add]["<{}_{}>".format(node_name, node_id)].append(
                    "{}(<{}_{}>)".format(relation_type, parent_node['class_name'], parent_node_id[0]))
            else:
                return_dict[key_to_add]["<{}_{}>".format(node_name, node_id)] = ["{}(<{}_{}>)".format(
                    relation_type, parent_node['class_name'], parent_node_id[0])]
    return return_dict


def populate_environment(graph, start_objects, start_room):
    environment = {
        "assets": [],
        "asset_states": {},
        "objects": [],
        "object_states": {},
    }
    # Create a mapping from each node ID to its corresponding node data
    id_to_node = {node['id']: node for node in graph['nodes']}
    # note that there are multiple nodes with the same name
    name_to_id = {}
    for node in graph['nodes']:
        if node['class_name'] in name_to_id.keys():
            name_to_id[node['class_name']].append(node['id'])
        else:
            name_to_id[node['class_name']] = [node['id']]
    # Create a mapping from child node ID to its parent node ID
    child_to_parent = {}
    for edge in graph['edges']:
        if edge['from_id'] in child_to_parent.keys():
            child_to_parent[edge['from_id']].append(
                (edge['to_id'], edge['relation_type']))
        else:
            child_to_parent[edge['from_id']] = [
                (edge['to_id'], edge['relation_type'])]
    objects_to_check = [remove_brackets(name) for name in start_objects]

    while objects_to_check:
        current_object = objects_to_check.pop()
        # print(objects_to_check)
        if "<{}>".format(current_object) not in environment["objects"] and "<{}>".format(
                current_object) not in environment["assets"]:
            # add to the environment
            if 'GRABBABLE' in id_to_node[int(
                    current_object.split('_')[-1])]['properties']:
                environment["objects"].append("<{}>".format(current_object))
            else:
                environment["assets"].append("<{}>".format(current_object))

            # find the parent and add the relationship to the environment
            parent_info = find_parent_node(
                graph, remove_brackets(current_object), start_room)
            if parent_info is not None:
                if "object_states" in parent_info:
                    for obj, states in parent_info["object_states"].items():
                        # add states to the environment
                        environment["object_states"]["<{}>".format(remove_brackets(obj))] = ["{}(<{}>)".format(
                            state.split('(')[0], remove_brackets(state.split('(')[-1].split(')')[0])) for state in states]
                        # add the new objects involved in the states to the
                        # list of objects to check
                        for state in states:
                            involved_object = remove_brackets(
                                state.split('(')[-1].split(')')[0])
                            if "<{}>".format(involved_object) not in environment["objects"] and "<{}>".format(
                                    involved_object) not in environment["assets"]:
                                objects_to_check.append(involved_object)
                if "asset_states" in parent_info:
                    for obj, states in parent_info["asset_states"].items():
                        # add states to the environment
                        environment["asset_states"]["<{}>".format(remove_brackets(obj))] = ["{}(<{}>)".format(
                            state.split('(')[0], remove_brackets(state.split('(')[-1].split(')')[0])) for state in states]
                        # add the new assets involved in the states to the list
                        # of assets to check
                        for state in states:
                            # remove brackets while keeping the ID
                            involved_asset = remove_brackets(state.split(
                                '(')[-1].split(')')[0])  # remove the ID and brackets
                            if "<{}>".format(involved_asset) not in environment["assets"] and "<{}>".format(
                                    involved_asset) not in environment["objects"]:
                                objects_to_check.append(involved_asset)
    # want to add 'object_properties' to the environment
    asset_properties = {}
    for asset in environment['asset_states']:
        asset_id = asset.strip('>').strip('<').split('_')[1]
        tmp_properties = []
        if "CAN_OPEN" in id_to_node[int(asset_id)]['properties']:
            tmp_properties.append("IS_OPENABLE")
        else:
            tmp_properties.append("NOT_OPENABLE")
        asset_properties[asset] = tmp_properties
    environment['asset_properties'] = asset_properties
    object_properties = {}
    for obj in environment['object_states']:
        obj_id = obj.strip('>').strip('<').split('_')[1]
        tmp_properties = []
        if "CAN_OPEN" in id_to_node[int(obj_id)]['properties']:
            tmp_properties.append("IS_OPENABLE")
        else:
            tmp_properties.append("NOT_OPENABLE")
        object_properties[obj] = tmp_properties
    environment['object_properties'] = object_properties
    return environment


def find_unique_objects(graph, object_name, start_room):
    hit_object = find_parent_node(graph, object_name, start_room)
    if hit_object is None:
        return []
    if len(hit_object['object_states']) > 0:
        object_list = hit_object['object_states'].keys()
    elif len(hit_object['asset_states']) > 0:
        object_list = hit_object['asset_states'].keys()
    else:
        # error
        raise ValueError('No object found')
    return list(object_list)


def extract_objects(script):
    objects_all = []
    for action in script:
        parts = action.split('(')
        arguments = parts[1].replace(" ", "").strip(')')
        # Check if there are any objects
        if len(arguments) == 0:
            objects = []
        else:
            objects = arguments.split(',')
        objects_all.extend(objects)
    return list(set(objects_all))


class ChatGPT_api:
    def __init__(self, credentials, prompt_load_order):
        openai.organization = credentials["openai"]["YOUR_ORG_ID"]
        openai.api_key = credentials["openai"]["OPENAI_API_KEY"]
        self.credentials = credentials
        self.messages = []
        self.max_token_length = 15000  # 4000
        self.max_completion_length = 2000  # 1300
        self.last_response = None
        self.last_response_raw = None
        self.query = ''
        self.instruction = ''
        # load prompt file
        fp_system = os.path.join(dir_system, 'system.txt')
        with open(fp_system) as f:
            data = f.read()
        self.system_message = {"role": "system", "content": data}

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

    def create_prompt(self):
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
        # json part is between ```python and ```.
        # skip if there is no json part
        if text.find('```python') == -1:
            return text
        text_json = text[text.find(
            '```python') + len('```python'):text.find('\n```')]
        text_json.replace('```', '')
        return text_json

    def generate(self, message, environment, is_user_feedback=False):
        if is_user_feedback:
            self.messages.append({'sender': 'user',
                                  'text': message})
        else:
            text_base = self.query
            if text_base.find('[ENVIRONMENT]') != -1:
                text_base = text_base.replace(
                    '[ENVIRONMENT]', json.dumps(environment))
            if text_base.find('[INSTRUCTION]') != -1:
                text_base = text_base.replace('[INSTRUCTION]', message)
                self.instruction = text_base
            self.messages.append({'sender': 'user', 'text': text_base})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=self.create_prompt(),
            temperature=2.0,
            max_tokens=self.max_completion_length,
            top_p=0.5,
            frequency_penalty=0.0,
            presence_penalty=0.0)
        text = response['choices'][0].message.content
        self.last_response_raw = text
        self.messages.append(
            {"sender": "assistant", "text": self.last_response_raw})
        # analyze the response
        self.last_response = text
        self.last_response = self.extract_json_part(self.last_response)
        self.last_response = self.last_response.replace("'", "\"")
        try:
            self.json_dict = json.loads(self.last_response, strict=False)
            self.environment = self.json_dict["environment_after"]
        except BaseException:
            self.json_dict = None
            return None
        return self.json_dict


def test_execution(comm, script):
    reset(comm)
    print('Starting scene...')
    comm.add_character('Chars/Male2', initial_room='kitchen')
    for i, script_atom in enumerate(script):
        task = text["task_cohesion"]["task_sequence"][i]
        task_atom = script_atom.split("[")[1].split("]")[0]
        ret = comm.render_script([script_atom], frame_rate=10, recording=True)
        if ret[0] is False:
            feedback = "You are wrong! Modify your answer. The following line failed in a simulator: " + task + "\n" + \
                "The verb {" + task_atom + "} is not applicable to the object(s). Refer to \'HUMAN ACTION LIST\' in my instruction."
            return feedback
    return ""


if __name__ == '__main__':
    comm = UnityCommunication()
    dir_name = "out_task_planning_gpt-3.5-turbo-16k_temp=2.0"
    waittime_sec = 30
    max_trial = 5
    time_api_called = time.time() - waittime_sec
    for scenario_id in range(1, 15):
        for trial_idx in range(max_trial):
            print(f"scenario_id={scenario_id}, trial_idx={trial_idx}")
            scenario_name = 'scenario_' + str(scenario_id)
            dump_name = './' + dir_name + f'/{scenario_name}/{trial_idx}'
            fp = os.path.join(dump_name + '.json')
            if os.path.exists(fp):
                continue
            with open('scenarios/' + str(scenario_id) + '.json') as f:
                scenario = json.load(f)
            instructions = scenario['instructions']
            reference_program = scenario['program']
            print(
                f"instructions(scenario_id={scenario_id}): {instructions[0]}")
            reset(comm)
            s, graph = comm.environment_graph()
            environment = populate_environment(
                graph, extract_objects(reference_program), "kitchen")
            scenario_name = 'scenario_' + str(scenario_id)
            if not os.path.exists('./' + dir_name + '/' + scenario_name):
                os.makedirs('./' + dir_name + '/' + scenario_name)
            while True:
                # if api is called within 60 seconds, wait
                current_time = time.time()
                if current_time - time_api_called < waittime_sec:
                    print("waiting for " + str(waittime_sec -
                          (current_time - time_api_called)) + " seconds...")
                    time.sleep(waittime_sec - (current_time - time_api_called))
                aimodel = ChatGPT_api(
                    credentials, prompt_load_order=prompt_load_order)
                text = aimodel.generate(
                    instructions[0],
                    environment,
                    is_user_feedback=False)
                time_api_called = time.time()
                if text is not None:
                    break
                else:
                    print("api call failed. retrying...")
                    current_time = time.time()
                    if current_time - time_api_called < waittime_sec:
                        print("waiting for " + str(waittime_sec -
                              (current_time - time_api_called)) + " seconds...")
                        time.sleep(waittime_sec -
                                   (current_time - time_api_called))
                    text = aimodel.generate(
                        "Your return cannot be interpreted as a valid json dictionary. Please reformat your response.",
                        environment,
                        is_user_feedback=True)
                    break
            if text is None:
                dump_name = './' + dir_name + f'/{scenario_name}/note'
                fp = os.path.join(dump_name + '.txt')
                # In the file, note that the trial was skipped
                with open(fp, 'w') as f:
                    f.write(aimodel.last_response)
                continue

            print("self test is running...")
            script = generate_script(text["task_cohesion"]["task_sequence"])
            user_feedback = test_execution(comm, script)
            if len(user_feedback) > 0:
                # VirtualHome sometimes fails to execute the script even if the
                # script is correct, so retry once just in case.
                user_feedback = test_execution(comm, script)
            print('result of self test: ' + user_feedback)
            was_execution_successful = False
            if len(user_feedback) > 0:
                was_execution_successful = False
            else:
                was_execution_successful = True
            dump_name = './' + dir_name + f'/{scenario_name}/{trial_idx}'
            fp = os.path.join(dump_name + '.json')
            aimodel.json_dict['was_execution_successful'] = was_execution_successful
            aimodel.json_dict['user_feedback'] = user_feedback
            with open(fp, 'w') as f:
                json.dump(aimodel.json_dict, f, indent=4)
