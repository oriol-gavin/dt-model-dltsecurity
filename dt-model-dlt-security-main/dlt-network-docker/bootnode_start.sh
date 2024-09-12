#!/bin/bash

# Read environment variables from .env file
source .env

# Start the bootnode service.
bootnode -nodekey ./bootnode/boot.key -verbosity 9 -addr $BOOTNODE_IP:$BOOTNODE_PORT 
