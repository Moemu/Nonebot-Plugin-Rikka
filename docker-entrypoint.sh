#!/bin/sh
set -eu

nb orm upgrade
nb run

exec "$@"