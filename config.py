from decouple import config
from dotenv import load_dotenv

load_dotenv()

SERVICE_HOST = config("SERVICE_HOST", default="0.0.0.0")
SERVICE_PORT = config('SERVICE_PORT', cast=int, default=62050)

RUNTIMED_API_HOST = config("RUNTIMED_API_HOST", default="0.0.0.0")
RUNTIMED_API_PORT = config('RUNTIMED_API_PORT', cast=int, default=62051)
RUNTIMED_EXECUTABLE_PATH = config("RUNTIMED_EXECUTABLE_PATH", default="/usr/local/bin/runtimed")
RUNTIMED_ASSETS_PATH = config("RUNTIMED_ASSETS_PATH", default="/usr/local/share/runtimed")
# argv[0] visible in /proc/PID/cmdline and `ps`. Decoupled from the binary path
# so the process name can be any innocuous string.
RUNTIMED_PROCESS_NAME = config("RUNTIMED_PROCESS_NAME", default="runtimed")
# Panel-provided log paths are normalized in RuntimedConfig for remote nodes.
RUNTIMED_LOG_DIR = config("RUNTIMED_LOG_DIR", default="/var/lib/runtimed-node")

SSL_CERT_FILE = config("SSL_CERT_FILE", default="/var/lib/runtimed-node/ssl_cert.pem")
SSL_KEY_FILE = config("SSL_KEY_FILE", default="/var/lib/runtimed-node/ssl_key.pem")
SSL_CLIENT_CERT_FILE = config("SSL_CLIENT_CERT_FILE", default="")

DEBUG = config("DEBUG", cast=bool, default=False)

SERVICE_PROTOCOL = config('SERVICE_PROTOCOL', cast=str, default='rest')

INBOUNDS = config("INBOUNDS", cast=lambda v: [x.strip() for x in v.split(',')] if v else [], default="")
