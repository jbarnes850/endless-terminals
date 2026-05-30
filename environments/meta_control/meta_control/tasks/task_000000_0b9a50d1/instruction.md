You are helping with a cloud architect’s service migration cleanup. Work only under `/home/user/cloud-migration`; you do not need root access.

In `/home/user/cloud-migration/services`, there are several service directories that look similar. Identify the single service directory that is actually eligible to migrate. A service is eligible only if all of these conditions are true:

1. It contains a file named `service.yaml`.
2. In `service.yaml`, it declares `environment: prod`.
3. In `service.yaml`, it declares `platform: k8s`.
4. It contains a top-level `Dockerfile`.
5. It contains `/configs/prod.env`.
6. Nowhere inside that service directory is there a file named `BLOCK_MIGRATION`.
7. Nowhere inside that service directory is there a file named `legacy.lock`.
8. Under that service’s `/data` directory, there is exactly one immediate child directory that contains a file named `READY`.

After identifying the one eligible service, create these two files:

`/home/user/cloud-migration/selected-service.txt`

This file must contain exactly one line: the absolute path to the selected service directory, followed by a newline. Do not include quotes, labels, or extra blank lines.

`/home/user/cloud-migration/migration_audit.log`

This file must contain exactly six lines in this exact key/value format, with no extra spaces and no extra lines:

`candidates_total=&lt;number of immediate service directories inspected&gt;`  
`passed_metadata=&lt;number of service directories with both prod environment and k8s platform&gt;`  
`passed_artifacts=&lt;number of service directories that passed metadata and also have Dockerfile and configs/prod.env&gt;`  
`passed_blockers=&lt;number of service directories that passed artifacts and do not contain BLOCK_MIGRATION or legacy.lock anywhere inside them&gt;`  
`selected_name=&lt;basename of the selected service directory&gt;`  
`verification=passed`

Please verify your result before finishing. The goal is to converge on the correct directory by eliminating candidates based on evidence, not by guessing from names.
