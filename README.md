# VRT Bridge

Convert a raw I/Q stream into VRT (VITA-49) packets.

## Usage

To start the service:

```shell
docker run \
    --rm \
    --volume="$(pwd)/config:/config:ro" \
    vrt-bridge \
    --config=/config/config.yml
```
