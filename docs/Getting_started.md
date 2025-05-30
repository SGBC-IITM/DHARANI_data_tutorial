Dharani/docs/Getting started

[Back] to `docs`

[Back]:README.md

The tutorial is compatible with local setup, as well as cloud.
For cloud instructions, see the [Google Colab](#google-colab), [AWS Sagemaker studio lab](#aws-sagemaker-studio-lab), and [Github codespace](#github-codespace).

If you prefer a local environment, jump to [Local Setup](#local-setup).

## Try on cloud 

|Pros: | cons|
|:--- | :---|
| * zero setup <br> * co-pilot possibilities, vibe coding <br>* try from anywhere (e.g., tablet PC)| * usage limits (for free tier)|

We provide guides here for popular cloud options: 
* [Google Colab](#google-colab) a familiar notebook interface, 
* [AWS Sagemaker studio lab](#aws-sagemaker-studio-lab), a jupyter lab interface, 
* [Github codespace](#github-codespace), which virtualizes VS Code on cloud, and serves as a ready-to-use dev environment for this repository.

### Google Colab
1. `Open` a notebook in colab

In your web browser, visit https://colab.research.google.com

In the popup, select 'Github' on the left listing, and enter 
https://github.com/sgbc-iitm/DHARANI_data_tutorial, and click search

The repository notebooks should be listed, as shown in the screenshot below.
Select the notebook you want to execute

![colab open screen](../assets/colab_new_screen.png) 

2. `Begin`` by Creating two blocks at the top of the notebook, 

Copy the below code and paste in the first block
 ```
! git clone https://github.com/sgbc-iitm/DHARANI_data_tutorial.git && pip install -r DHARANI_data_tutorial/requirements_3.10.txt
```

and execute it. Then copy-paste the below block

```
import sys
sys.path.append('DHARANI_data_tutorial')
```
and execute it.

3. Proceed with executing the rest of the blocks in the notebook.

### AWS Sagemaker Studio Lab

Please register at https://studiolab.sagemaker.aws/ for a free account. 

Visit the developer guide at https://docs.aws.amazon.com/sagemaker/latest/dg/studio-lab-onboard.html for help.

Activate your account (might involve few days waiting for an approval email). Then create account, and start runtime.

![smslinstance]

[smslinstance]: ../assets/studiolab_launch.png

Provide mobile number if asked, and verify with OTP sent to mobile.

- Open project
![smsllaunch]

[smsllaunch]:../assets/studiolab_open_project.png

- Clone git repo

Left vertical panel 3rd option --> 'Clone a Repository' --> enter Dharani tutorial https git clone url
![smslclone]

[smslclone]: ../assets/studiolab_clone_git.png

- On left panel showing the repo files, navigate to notebooks folder, and select the notebook file (.ipynb) you wish to execute, to open it in the main panel.

- In the notebook, insert code block to type and execute the following
```
!pip install -e ../requirements_3.10.txt
```
![smslscreen]

[smslscreen]:../assets/studiolab_notebook_preamble.png

- Continue executing the rest of the notebook.

### Github Codespace
1. Login to Github.com, and visit the Dharani tutorial repository (https://github.com/SGBC-IITM/DHARANI_data_tutorial/)

2. Click the green button `Code` and toggle to `Codespace`. Click `Create codespace on main`.

![codespace-create]

3. Once the codespace is setup (appears like VS Code within your browser window), you can navigate to the notebooks folder, select any notebook, and begin working. 

To bring out the Github Co-pilot, use the icon on the top panel. You can connect to GPT-4o, or other AI models (might require account with the respective AI model provider) on the right panel, and chat about the code, ask for help, or make it write code to implement the functionality you desire.
![codespace-copilot]

4. To stop the codespace, click the bottom left blue bar, which might say something like `Codespaces: fancynameof thecodespace`, to get a pulldown menu, having options like `Stop Current Codespace`, and more options. Use this to stop the codespace. Note: It will remain stopped, but not ended, so you can go to your codespaces page (https://github.com/codespaces) and restart it if you want, or delete the codespace.

![codespace-control]

![codespace-delete]

[codespace-create]:../assets/codespace_create.png
[codespace-copilot]:../assets/codespace_copilot.png
[codespace-control]:../assets/codespace_control.png
[codespace-delete]:../assets/codespace_delete.png


## Local setup
This is the regular workflow, of setting up the codes in your own computer at a designated folder, preparing the environment, and working within the environment.

Operational familiarity with a command line is required.

1. `clone` this github repository to your computer
[[cloning guidance]]

```
git clone https://github.com/SGBC-IITM/DHARANI_data_tutorial.git
```

[cloning guidance]: https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository

2. `get` prerequisites: python3.10 or newer; refer [python setup]

[python setup]: https://docs.python.org/3/using/index.html

3. `create` and `activate` python environment [[env guidance]]

``` 
python3 -m venv dharani_env
```

[windows]
``` 
source dharani_env\Scripts\activate
```

[*nix] 
```
 dharani_env/bin/activate
 ```

[env guidance]: https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/

4. `populate` the environment with packages listed in requirements_3.10.txt

```
pip install -r requirements_3.10.txt
```

## Regular use
  `activate` dharani_env, then

5. `start` jupyter [[starting]]

``` 
jupyter notebook
```

[starting]:https://docs.jupyter.org/en/latest/running.html

6. `open` jupyter in browser

```http://localhost:8888/tree```

7. Begin working

 Click a `ipynb` file in the `notebooks` folder to open it for running, or `create` a new notebook and start entering and evaluating code.

Enable the **ToC side bar** in the jupyter notebook 

*Menu Navigation* :: View->Left Sidebar -> Show Table of Contents

Refer [HowTo] for details. View or submit [issues] if any.

[HowTo]: HOWTO.md
[issues]: https://github.com/SGBC-IITM/DHARANI_data_tutorial/issues/
