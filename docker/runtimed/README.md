# Docker image and `runtimed` binary

The **Dockerfile** does not use this folder for the binary anymore. It downloads the latest **`runtimed`** release from [spawni777/runtimed](https://github.com/spawni777/runtimed) at build time.

## Release asset names

Each published release should include Linux executables attached with these names (so `…/releases/latest/download/…` resolves correctly):

- `runtimed-linux-amd64`
- `runtimed-linux-arm64`

They are installed in the image as `/usr/local/bin/runtimed`.

## Overrides

Build arguments (see root `Dockerfile`):

- `RUNTIMED_REPO` — default `spawni777/runtimed`
- `TARGETARCH` — `amd64` or `arm64` (Buildx sets this per platform)
- `RUNTIMED_BINARY_URL` — if set, download this URL instead of the latest-release pattern above

## Optional local assets

To ship extra files under `/usr/local/share/runtimed/` in a custom image, extend the Dockerfile or mount files at runtime; the default fetch step only creates an empty `share` directory layout.
