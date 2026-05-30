You are helping with a small deployment rollout audit for a Python utility in `/home/user/deploy-rollout`. The application code and dependency list are already present there. Please prepare an isolated Python virtual environment with `venv`, install the application dependencies into it, run the existing utility, and write a deployment evidence file that our automated checker can read.

The working directory is `/home/user/deploy-rollout`. It contains:
- `/home/user/deploy-rollout/requirements.txt`
- `/home/user/deploy-rollout/rollout_probe.py`

Your final system state must satisfy all of the following, without requiring root access:

1. Create a Python virtual environment at exactly:
   `/home/user/deploy-rollout/.venv`

2. Install the dependencies from:
   `/home/user/deploy-rollout/requirements.txt`
   into that virtual environment, not into the system Python environment.

3. Run the rollout probe using the Python interpreter inside the virtual environment. The probe is:
   `/home/user/deploy-rollout/rollout_probe.py`

4. Create a plain-text deployment evidence file at exactly:
   `/home/user/deploy-rollout/deployment_evidence.log`

5. The evidence file must contain exactly 8 lines, in this exact order and with these exact field names:

   Line 1:
   `status=ready`

   Line 2:
   `venv_path=/home/user/deploy-rollout/.venv`

   Line 3:
   `python_executable=<absolute path to the python executable inside the virtual environment>`

   Line 4:
   `pip_executable=<absolute path to the pip executable inside the virtual environment>`

   Line 5:
   `requests_version=<installed requests version visible inside the virtual environment>`

   Line 6:
   `probe_result=<single-line result printed by rollout_probe.py when run with the virtualenv python>`

   Line 7:
   `site_scope=venv`

   Line 8:
   `deployment_note=dependencies installed and probe executed with isolated interpreter`

Important formatting requirements:
- Do not include blank lines.
- Do not include extra commentary before or after the 8 lines.
- Use absolute paths for `python_executable` and `pip_executable`.
- The `python_executable` path must point inside `/home/user/deploy-rollout/.venv`.
- The `pip_executable` path must point inside `/home/user/deploy-rollout/.venv`.
- The `requests_version` value must be obtained from the virtual environment after installation.
- The `probe_result` value must be copied from the actual output of running `/home/user/deploy-rollout/rollout_probe.py` with the virtual environment’s Python interpreter.
- If you activate the environment in your shell, still make sure the evidence file records absolute executable paths, not just `python` or `pip`.

Before finishing, verify that:
- `/home/user/deploy-rollout/.venv` exists,
- the virtual environment can import `requests`,
- the probe runs successfully using the virtual environment interpreter,
- `/home/user/deploy-rollout/deployment_evidence.log` has exactly the 8 required lines in the required order.
