#!/usr/bin/env bash
# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

set -e

# ANSI colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not installed. Please install git and try again.${NC}"
    exit 1
fi

# Clone the repository if we are not already inside the directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/google_workspace_mcp" ]; then
    echo -e "${YELLOW}Cloning google-workspace-mcp repository...${NC}"
    git clone https://github.com/wrik0/gws-workspace-agent.git
    cd gws-workspace-agent
fi

# Run the python setup script
if command -v python3 &> /dev/null; then
    python3 setup.py "$@"
else
    echo -e "${RED}Error: python3 is not installed. Please install Python 3.11+ and try again.${NC}"
    exit 1
fi
