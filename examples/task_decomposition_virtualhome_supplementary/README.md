This folder contains the prompts used for the experiment with VirtualHome (supplementary data). Please check the README.md in this folder for more details. We used [gpt-3.5-turbo-16k](https://platform.openai.com/docs/models/gpt-3-5) for the experiments. Codes in this folder use the [OpenAI API](https://platform.openai.com/docs/api-reference) to call ChatGPT. If you are using Azure OpenAI, set `use_azure` in aimode.py to True, and set `api_version` in aimode.py to '2022-12-01' (version 0301) or '2023-05-15' (any other version). By default, `use_azure` is set to False.

Directory structure should look like this:
```bash
this_folder
│───task_planning_addexamples.py
│───task_planning_detail.py
├───out_feedback_test_gpt-3.5-turbo-16k_temp=2.0_addexamples/
├───out_task_planning_gpt-3.5-turbo-16k_temp=2.0_detail/
│───system/
│───prompt/
│───query/
│───scenarios/
```
* task_planning_addexamples: a python script to test the performance of task planning across trials. An additional example of an open-put-close operation has been included in the prompt.
* task_planning_detail: a python script to test the performance of task planning across trials. The naming convention of actions has been modified in the prompt
* out_feedback_test_gpt-3.5-turbo-16k_temp=0.0_addexamples/: A folder for storing the output of ChatGPT for feedback_test.py. Sample data is compressed in .zip format.
* out_task_planning_gpt-3.5-turbo-16k_temp=2.0_detail/: A folder for storing the output of ChatGPT for task_planning.py. Sample data is compressed in .zip format.
* system/: Contains a text file to be inserted at the beginning of the prompt.
* prompt/: A folder for storing the prompts.
* query/: Contains a template for converting user input, which is loaded from scenarios/, into prompts.
* scenarios/: A folder for storing the scenarios used in the experiment.

**Please note that:**
This code uses [VirtualHome v2.3.0](http://virtual-home.org/documentation/master/index.html) and [the Python API](https://github.com/xavierpuigf/virtualhome) to communicate with the environment. The codes were tested with the API virtualhome==2.3.0.