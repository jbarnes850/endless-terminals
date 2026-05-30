You are helping an edge computing engineer prepare a deployable backup bundle for a small IoT gateway configuration. All work should happen under `/home/user/iot_gateway_deploy`.

The source configuration tree is located at:

`/home/user/iot_gateway_deploy/device_config`

Create exactly one compressed tar archive at:

`/home/user/iot_gateway_deploy/out/gateway-edge-backup.tar.gz`

The archive is intended to be copied directly to IoT devices, so its internal paths must be relative to the `device_config` directory. In other words, when the archive is listed, it must contain entries such as:

- `config.yaml`
- `network/interfaces.conf`
- `services/mqtt.env`
- `services/sensor-sampler.env`
- `certs/device.crt`
- `certs/device.key`
- `manifest.txt`

It must not contain absolute paths, and it must not contain a leading `device_config/` directory component.

The archive must include every regular file currently inside `/home/user/iot_gateway_deploy/device_config`, including files in subdirectories. It must preserve file names and directory structure relative to `device_config`.

After creating the archive, write a verification log at:

`/home/user/iot_gateway_deploy/out/backup_verification.log`

The log must be plain UTF-8 text with exactly these six lines in this order:

1. `archive=/home/user/iot_gateway_deploy/out/gateway-edge-backup.tar.gz`
2. `exists=yes`
3. `format=gzip-compressed-tar`
4. `root_prefix=none`
5. `file_count=7`
6. `status=verified`

The `file_count` line must reflect the number of regular files included in the archive. Do not count directory entries.

Before you finish, verify the actual contents of the archive rather than relying only on whether a command exited successfully. A clean command run is not sufficient if the archive paths are wrong or files are missing.
