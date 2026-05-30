You’re helping me clean up a small web developer workspace that recently changed its Python virtual environment location.

The project directory is `/home/user/projects/portfolio-site`. It currently has an old virtual environment path that should no longer be treated as the source of truth. I need the project switched to the new virtual environment location and verified from that new location only.

Please perform the following end-to-end update:

1. Create or repair the Python virtual environment at:
   `/home/user/projects/portfolio-site/.venv`

2. Make sure the new virtual environment contains a working Python interpreter and `pip`.

3. Retire the old virtual environment path:
   `/home/user/projects/portfolio-site/venv`

   The old path must not remain as an active virtual environment directory. It is acceptable for it to be absent, renamed, or otherwise made clearly inactive, but the project must not depend on it anymore.

4. Update the project’s environment pointer file:
   `/home/user/projects/portfolio-site/.envrc`

   Its final content must be exactly one line, ending with a newline:

   `source /home/user/projects/portfolio-site/.venv/bin/activate`

5. Verify the new virtual environment by running Python from the new environment, not from the old location and not from the system interpreter.

6. Write a verification log at:
   `/home/user/projects/portfolio-site/venv_migration_check.log`

   The automated checker will read this log, so please use this exact format:

   - The file must contain exactly 5 non-empty lines.
   - Each line must use `KEY=VALUE` format.
   - The required keys, in this exact order, are:

     `PROJECT_DIR`
     `ACTIVE_ENV`
     `PYTHON_EXE`
     `PIP_EXE`
     `OLD_ENV_STATUS`

   - `PROJECT_DIR` must be `/home/user/projects/portfolio-site`
   - `ACTIVE_ENV` must be `/home/user/projects/portfolio-site/.venv`
   - `PYTHON_EXE` must be the absolute path to the Python executable inside the new virtual environment.
   - `PIP_EXE` must be the absolute path to the pip executable inside the new virtual environment.
   - `OLD_ENV_STATUS` must describe the old environment path after retirement using one of these values only:
     `missing`, `renamed`, or `inactive`

Before finishing, verify the final state from `/home/user/projects/portfolio-site/.venv` itself. Do not rely on any output, activation state, or files from `/home/user/projects/portfolio-site/venv`, because that is the stale location being retired.
