# Use a base image with Ubuntu 
FROM ubuntu:20.04

# Set environment variables to avoid user interaction during the installation
ENV DEBIAN_FRONTEND=noninteractive


# Install the required software-properties-common package
RUN apt-get update && \
    apt-get install -y software-properties-common \
    iproute2 \
    iputils-ping 
 
# Add Ethereum PPA repository
RUN add-apt-repository -y ppa:ethereum/ethereum

# Update package list
RUN apt-get update

# Install Ethereum package (geth)
RUN apt-get install -y ethereum

# Set the working directory inside the container
WORKDIR /dlt-network

# Copy the entire directories and their contents into the container
COPY bootnode ./bootnode
COPY node1 ./node1
COPY node2 ./node2
COPY node3 ./node3
COPY node4 ./node4

# Copy the shell scripts and other files
COPY *_start.sh ./
COPY password.txt genesis.json ./

# Make bash scripts executable
RUN chmod +x *_start.sh



