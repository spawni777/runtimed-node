# Runtimed node

Python service that runs a local **`runtimed`** process and exposes a TLS API for remote control.

## Configuration

Copy `.env.example` to `.env` and adjust paths. Defaults assume state under `/var/lib/runtimed-node/`.

Environment variables use the `RUNTIMED_*` prefix (see `config.py`).

## Docker

The image downloads the **`runtimed`** binary from the **latest GitHub release** of [spawni777/runtimed](https://github.com/spawni777/runtimed) (see `docker/runtimed/README.md` for expected asset file names).

1. Build: `docker compose build`
2. Run: `docker compose up -d`

Override the download with build arg `RUNTIMED_BINARY_URL` if you need a fixed URL instead of `latest`.

## systemd

See `runtimed-node.service` — adjust `WorkingDirectory` and paths to match your deployment.
