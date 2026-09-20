#!/usr/bin/env bash

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: ./deploy_to_ec2.sh <EC2_PUBLIC_IP> [EC2_USER] [PEM_KEY_PATH]"
  exit 1
fi

export EC2_IP="$1"
export EC2_USER="${2:-ubuntu}"
export PEM_KEY="${3:-$HOME/Downloads/lal10myntra.pem}"

bash "$(cd "$(dirname "$0")" && pwd)/sync_to_ec2.sh"
