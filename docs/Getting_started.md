Dharani/docs/Getting started

[Back] to `docs`

[Back]:README.md

## Initial setup
Operational familiarity with a command line is required.

1. `clone` this github repository to your computer
[[cloning guidance]]

``` git clone https://github.com/SGBC-IITM/DHARANI_data_tutorial.git```

[cloning guidance]: https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository

2. `get` prerequisites: python3.10 or newer; refer [python setup]

[python setup]: https://docs.python.org/3/using/index.html

3. `create` and `activate` python environment [[env guidance]]

``` python3 -m venv dharani_env```

[windows] ``` source dharani_env\Scripts\activate```

[*nix] ``` dharani_env/bin/activate```

[env guidance]: https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/

4. `populate` the environment with packages listed in requirements_3.10.txt

```pip install -r requirements_3.10.txt```

## Regular use
  `activate` dharani_env, then

5. `start` jupyter [[starting]]

``` jupyter notebook```

[starting]:https://docs.jupyter.org/en/latest/running.html

6. `open` jupyter in browser

```http://localhost:8888/tree```

7. Begin working

 Click a `ipynb` file in the `notebooks` folder to open it for running, or `create` a new notebook and start entering and evaluating code.

Enable the ToC side bar in the jupyter notebook 

Menu Navigation:: View->Left Sidebar -> Show Table of Contents

Refer [HowTo] for details.

[HowTo]: ../docs/HOWTO.md
