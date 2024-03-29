This folder contains the prompts used for task decomposition from natural language in our paper, as well as examples of ChatGPT output. We used [gpt-35-turbo (0301)](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/concepts/models#chatgpt-gpt-35-turbo-preview) for the experiments. If you are using version 0301, set `api_version` in aimode.py to '2022-12-01'. For any other version, use '2023-05-15'. By default, `api_version` is set to '2022-12-01'. If you are using the OpenAI API instead of the Azure OpenAI, set `use_azure` in aimode.py to False. By default, `use_azure` is set to True.


We provide five example prompts for the following tasks:
* **task_decomposition**: This folder contains the prompts used for task decomposition from natural language.
* **task_decomposition_dual_arm**: This folder contains the prompts used for task decomposition from natural language for dual-arm robots.
* **task_decomposition_logic**: This folder contains the prompts used for task decomposition with conditional logic from natural language.
* **task_decomposition_virtualhome**: This folder contains the prompts used for the experiment with VirtualHome. Please check the README.md in this folder for more details.
* **task_decomposition_virtualhome_supplementary**: This folder contains the prompts used for the experiment with VirtualHome (supplementary data). Please check the README.md in this folder for more details.

Directory structure should look like this:
```bash
root_folder
│───aimodel.py
├───out/
│───prompt/
│───query/
│───system/
```
* aimodel.py: a python script for calling ChatGPT
* system/: Contains a text file to be inserted at the beginning of the prompt.
* prompt/: A folder for storing the prompts.
* query/: Contains a template for converting user input into prompts.
* out/: A folder for storing the output of ChatGPT.

**Please note that:**
* We conducted experiments that involved multi-step natural language instructions in various environments. The environment definitions and natural language instructions are written in **aimodel.py**.

* Some of the results shown in out/ include outputs that were re-generated by ChatGPT based on user feedback. Running **aimodel.py** allows for text feedback via standard input after ChatGPT's response to each natural language prompt.

[Microsoft's sample code for using ChatGPT](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python) will be helpful for understanding how to use the API.