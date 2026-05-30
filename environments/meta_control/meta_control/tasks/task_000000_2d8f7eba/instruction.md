You are helping a release manager prepare a deployment shell environment for a small service. Please update the deployment environment file and write a verification ledger so another teammate can confirm the work without re-running your commands.

Work only under `/home/user/release-prep`. The file `/home/user/release-prep/deploy.env` already exists and contains draft settings. Modify that file so that it is a valid shell-style environment file with exactly these public requirements:

1. Keep the existing variable names and make sure the final file contains exactly one assignment line for each of these variables, in this order:
   - `APP_NAME`
   - `DEPLOY_ENV`
   - `RELEASE_CHANNEL`
   - `REGION`
   - `CANARY_PERCENT`
   - `FEATURE_FLAGS`
2. Set the deployment environment for a production rollout:
   - `DEPLOY_ENV` must be `production`
   - `RELEASE_CHANNEL` must be `stable`
   - `REGION` must be `us-east-2`
   - `CANARY_PERCENT` must be `10`
3. Preserve the existing application name already present in the file.
4. The `FEATURE_FLAGS` value must be a comma-separated list with no spaces. It must include `audit_logging`, `metrics_v2`, and `safe_shutdown`, and it must not include duplicate flags.
5. The final `/home/user/release-prep/deploy.env` file must contain only the six assignment lines listed above: no comments, no blank lines, and no extra variables.

After editing the environment file, create `/home/user/release-prep/release_ledger.log`. This ledger is part of the deliverable and must have exactly seven lines in this format:

```text
CHECK 1 app_name_preserved=YES
CHECK 2 deploy_env_production=YES
CHECK 3 release_channel_stable=YES
CHECK 4 region_us_east_2=YES
CHECK 5 canary_percent_10=YES
CHECK 6 feature_flags_valid=YES
READY production_deployment_env=YES
```

Do not add any extra text before or after those seven lines. Before you finish, verify for yourself that both files meet the requirements exactly.
