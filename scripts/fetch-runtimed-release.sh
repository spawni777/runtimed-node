#!/usr/bin/env bash
# Installs runtimed into /usr/local/bin and geo assets into /usr/local/share/runtimed.
#
# Modes:
# 1) RUNTIMED_LOCAL_BINARY=/path/to/file — use a prebuilt binary (no GitHub download).
# 2) RUNTIMED_BINARY_URL — download that URL (full file URL).
# 3) Otherwise: download runtimed-linux-<arch> from ${REPO} GitHub releases.
#
# Env GEO_RULES_DAT_BASE optionally overrides the base URL for geosite.dat / geoip.dat.

set -euo pipefail

install -d /usr/local/bin
install -d /usr/local/share/runtimed

if [[ -n "${RUNTIMED_LOCAL_BINARY:-}" && -f "${RUNTIMED_LOCAL_BINARY}" ]]; then
  echo "fetch-runtimed-release: using local binary ${RUNTIMED_LOCAL_BINARY}"
  install -m0755 "${RUNTIMED_LOCAL_BINARY}" /usr/local/bin/runtimed
else
  REPO="${1:?owner/repo, e.g. spawni777/runtimed}"
  ARCH="${2:?amd64, arm64, ...}"

  TMP="$(mktemp)"
  trap 'rm -f "${TMP}"' EXIT

  if [[ -n "${RUNTIMED_BINARY_URL:-}" ]]; then
    echo "fetch-runtimed-release: using RUNTIMED_BINARY_URL"
    curl -fsSL -o "${TMP}" "${RUNTIMED_BINARY_URL}"
  else
    ASSET="runtimed-linux-${ARCH}"
    URL="https://github.com/${REPO}/releases/latest/download/${ASSET}"
    echo "fetch-runtimed-release: downloading ${URL}"
    if ! curl -fsSL -o "${TMP}" "${URL}"; then
      echo "fetch-runtimed-release: download failed. Place your binary at prebuilt/${ASSET} for local builds, publish a GitHub Release with \"${ASSET}\", or set RUNTIMED_BINARY_URL." >&2
      exit 1
    fi
  fi

  install -m0755 "${TMP}" /usr/local/bin/runtimed
  echo "fetch-runtimed-release: installed /usr/local/bin/runtimed from release or URL"
fi

GEO_BASE_DEFAULT="https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download"
GEO_BASE="${GEO_RULES_DAT_BASE:-${GEO_BASE_DEFAULT}}"

echo "fetch-runtimed-release: downloading geosite.dat and geoip.dat from ${GEO_BASE}"
curl -fsSL -o /usr/local/share/runtimed/geosite.dat "${GEO_BASE}/geosite.dat"
curl -fsSL -o /usr/local/share/runtimed/geoip.dat "${GEO_BASE}/geoip.dat"
echo "fetch-runtimed-release: installed geo assets under /usr/local/share/runtimed"
