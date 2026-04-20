#!/usr/bin/env bash
# Installs the runtimed binary and optional geo/asset files into the image.
# Usage: install-runtimed.sh <source_directory>
# Expected layout under source_directory:
#   runtimed          — required executable
#   share/            — optional; copied to /usr/local/share/runtimed/

set -euo pipefail

SRC="${1:?source directory required}"

if [[ ! -f "${SRC}/runtimed" ]]; then
  echo "install-runtimed: missing ${SRC}/runtimed — place your built binary there before docker build." >&2
  exit 1
fi

install -d /usr/local/bin
install -m0755 "${SRC}/runtimed" /usr/local/bin/runtimed

install -d /usr/local/share/runtimed
if [[ -d "${SRC}/share" ]] && compgen -G "${SRC}/share/*" >/dev/null; then
  cp -a "${SRC}/share/." /usr/local/share/runtimed/
fi

echo "install-runtimed: installed /usr/local/bin/runtimed"
