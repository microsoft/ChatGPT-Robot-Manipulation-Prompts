This folder contains the prompts used for the experiment with VirtualHome. Please check the README.md in this folder for more details. We used [gpt-3.5-turbo-16k](https://platform.openai.com/docs/models/gpt-3-5) for the experiments. Codes in this folder use the [OpenAI API](https://platform.openai.com/docs/api-reference) to call ChatGPT.

Directory structure should look like this:
```bash
this_folder
│───feedback_test.py
│───task_planning.py
├───out_feedback_test_gpt-3.5-turbo-16k_temp=0.0/
├───out_task_planning_gpt-3.5-turbo-16k_temp=2.0/
│───system/
│───prompt/
│───query/
│───scenarios/
```
* feedback_test.py: a python script to test the performance of task planning across trials.
* task_planning.py: a python script to test the adjustment functionality through auto-generated feedback.
* out_feedback_test_gpt-3.5-turbo-16k_temp=0.0/: A folder for storing the output of ChatGPT for feedback_test.py.
* out_task_planning_gpt-3.5-turbo-16k_temp=2.0/: A folder for storing the output of ChatGPT for task_planning.py.
* system/: Contains a text file to be inserted at the beginning of the prompt.
* prompt/: A folder for storing the prompts.
* query/: Contains a template for converting user input, which is loaded from scenarios/, into prompts.
* scenarios/: A folder for storing the scenarios used in the experiment.

**Please note that:**
This code uses [VirtualHome v2.3.0](http://virtual-home.org/documentation/master/index.html) and [the Python API](https://github.com/xavierpuigf/virtualhome) to communicate with the environment. The codes were tested with the API virtualhome==2.3.0.