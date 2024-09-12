# DLT Network with Docker and Geth

This repository contains the necessary files to Deploy a DLT locally and try a demo of the model-sharing workflow desgined using it 

## Files
code: This directory contains all the implementations in Solidity and Python to run the workflow.

dlt-network-docker: This directory contains all the files to deploy the DLT in a docker environment locally.

requirements.tx. This .txt file contains a list of all the libraries installed and the versions.

## DLT Deployment

### Prerequisites

Make sure you have Docker on your system before proceeding.

- [Install Docker](https://docs.docker.com/engine/install/ubuntu/)

### Build the Docker Image

To build the Docker image, run the following command in the root directory of the project:

```bash
docker build -t dlt-node .
```

### Starting the DLT Network

Start the DLT network with the following command:

```bash
docker-compose up -d
```

The Docker Compose file will first create a single bootnode container that serves as the entry point for the network. Then, it will create four dlt nodes that automatically connect to the bootnode. All containers will be isolated within a private network with static IP addresses.

To stop the network, use:

```bash
docker-compose down
```

### Verifying Node Association

After starting the DLT network, you can verify that the nodes have associated correctly by executing the following commands:

```bash
docker exec -it node1 geth --exec "net.peerCount" attach ws://node1:3334
```
```bash
docker exec -it node2 geth --exec "net.peerCount" attach ws://node2:3335
```
```bash
docker exec -it node3 geth --exec "net.peerCount" attach ws://node3:3336
```
```bash
docker exec -it node4 geth --exec "net.peerCount" attach ws://node4:3337
```
Each command should display 3 peers, indicating that the nodes have successfully connected to each other.

### Additional Utility Commands

For additional utility commands, you can use:

```bash
docker exec -it node1 geth --exec "clique.getSigners()" attach ws://node1:3334
docker exec -it node1 geth --exec "eth.getBalance(eth.accounts[0])" attach ws://node1:3334
```

## Running the demo 
In order to see how the workflow is actually working, run the following steps. Is highly important to have installed docker and deployed the DLT properly.

First step is to open a terminal different from the one where the docker is running and travel to the code directory.

```bash
cd UTILS/code
```

Then, run the SDN_Controler. 

```bash
./SDN_Controller.py
```
Once running, choose the API port number (usually 5001).

In another terminal, run the DT (./code/DT.py). 

```bash
./DT.py
```
Once running choose the port number (usually 5000).

Write down in the json file ports_info.json (./code/ports_info.json) the chosen ports for the DT and SDN in the proper place.

In another terminal, run the Network Orchestrator. 

```bash
./NetworkOrchestrator.py
```
Once running, will ask for the Smart Contract name, write MasContract.sol.

Finally, when the NetworkOrchestrator execution is done, we can press number 4 in the DT terminal, and we will see the messages of the workflow.