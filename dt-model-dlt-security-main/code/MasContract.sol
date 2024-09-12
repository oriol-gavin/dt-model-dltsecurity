// SPDX-License-Identifier: MIT
pragma solidity ^0.8.12;
contract MasContract {

    // VxLAN Secret key
    string private secretKey;
    // Array of the ids of the models
    int[] private ids;
    // Array of the names of the models
    string[] private names;
    // Integer for the model ids;
    int private nextId;

    // Enum defining participant roles
    enum Role { Agent, MLFO }

    // Mapping to track registered participants
    mapping(address => Participant) public participant;

    // Struct to represent a participant (SDN or MLFO)
    struct Participant {
        string name;
        bool registered;
        Role role;
    }
    // Struct to represent a Model
    struct ModelSerialized {
        int id;
        int model_type;
        string name;
        bytes info;
    }

    // Array of models
    ModelSerialized[] private models;

    // Event emitted when a participant is registered
    event ParticipantRegistered(address participant, string name);

    // Event emitted when a participant is unregistered
    event ParticipantUnregistered(address agentAddress, string agentName);

    // Event emitted when a participant is deleted
    event ParticipantDeleted(address agentAddress, string agentName);

    // Event emitted when the MLFO sets a new secret key
    event SecretKeySet(address mlfo);

    // Event emitted when the client adds a new Model to return the id
    event ModelConfigAdded(int id);

    // Event emitted when the client adds a new Model to return the model
    event NewModel(bytes model, int modelType);

    // Constructor to initialize the contract and register the MLFO
    constructor() {
        // Set the initial secret key to an empty string
        secretKey = "";
        nextId = 1;
        // Register the deploying address as an MLFO participant
        participant[msg.sender] = Participant({
                name: "MLFO",
                registered: true,
                role: Role.MLFO
        });
        emit ParticipantRegistered(msg.sender, "MLFO");
    }

    // Function to register a select group of N Agents in the smart contract, can only be called by the MLFO
    function registerAgents(address[] memory agentAddresses, string[] memory agentNames) public {
        // Ensure that only the MLFO calls the function
        require(participant[msg.sender].role==Role.MLFO, "Only the MLFO can register Agents");

        // Loop through the agentAddresses array and register the agents
        for (uint256 i = 0; i < agentAddresses.length; i++) {
            address agentAddress = agentAddresses[i];
            string memory agentName = agentNames[i];

            // Ensure that the agent name is not empty
            require(bytes(agentName).length > 0, "Name is not valid");

            // Ensure that the agent is not already registered
            require(participant[agentAddress].registered == false, "Agent already registered");

            // Register the agent
            participant[agentAddress] = Participant({
                name: agentName,
                registered: true,
                role: Role.Agent
            });

            // Emit the event to notify the registration of the agent
            emit ParticipantRegistered(agentAddress, agentName);
        }
    }

    function unregisterAgents(address[] memory agentAddresses, string[] memory agentNames) public {
        // Ensure that only the MLFO calls the function
        require(participant[msg.sender].role==Role.MLFO, "Only the MLFO can unregister Agents");

        // Loop through the agentAddresses array and unregister the agents
        for (uint256 i = 0; i < agentAddresses.length; i++) {
            address agentAddress = agentAddresses[i];
            string memory agentName = agentNames[i];

            // Ensure that the agent name is not empty
            require(bytes(agentName).length > 0, "Name is not valid");

            // Ensure that the agent is not already registered
            require(participant[agentAddress].registered == true, "Agent not registered");

            // Unregister the agent
            participant[agentAddress] = Participant({
                name: agentName,
                registered: false,
                role: Role.Agent
            });

            // Emit the event to notify the registration of the agent
            emit ParticipantUnregistered(agentAddress, agentName);
        }
    }

    function deleteAgents(address[] memory agentAddresses, string[] memory agentNames) public {
        // Ensure that only the MLFO calls the function
        require(participant[msg.sender].role==Role.MLFO, "Only the MLFO can register Agents");

        // Loop through the agentAddresses array and unregister the agents
        for (uint256 i = 0; i < agentAddresses.length; i++) {
            address agentAddress = agentAddresses[i];
            string memory agentName = agentNames[i];
            // Delete the agent
            delete participant[agentAddress];
            // Emit the event to notify the registration of the agent
            emit ParticipantDeleted(agentAddress, agentName);
        }
    }

    // Returns participant's name and its role
    function getParticipantInfo(address participant_address) public view returns (string memory name, Role) {
        Participant storage current_participant = participant[participant_address];
        require(current_participant.registered == true, "Participant is not registered with this address. Please register.");
        return (current_participant.name, current_participant.role);
	}

    // Function to set the secret key for the agents communication, can only be called by the MLFO
    function setSecretKey(string memory key) public {
        Participant storage current_participant = participant[msg.sender];
        require(current_participant.registered==true, "Participant is not registered. Can not look into. Please register.");
        require(current_participant.role==Role.MLFO, "Only the MLFO can set the secret key");
        secretKey = key;
        emit SecretKeySet(msg.sender);
    }

    // Function to retrieve the secret key, can only be called by registered participants
    function getSecretKey(address call_address) public view returns (string memory) {
        Participant storage current_participant = participant[call_address];
        require(current_participant.registered == true, "Participant is not registered. Can not look into. Please register.");
        return secretKey;
    }

    // FUNCTIONS FOR THE MODEL CONTROL

    // Add an entry to the models array
    function addModelSerialized(address call_address, string memory name, bytes memory info, int mt) public {
        Participant storage current_participant = participant[call_address];
        require(current_participant.registered == true, "Participant is not registered. Please register, ask the Orchestrator for a valid account.");

        models.push(ModelSerialized(nextId, mt, name, info));
        ids.push(nextId);
        names.push(name);
        emit ModelConfigAdded(nextId);
        emit NewModel(info, mt);
        nextId++;
   }
    // Add info to the model with Id = id
    function addWeightsToBlockWithId(int id, bytes memory chunk) public{
        uint arrayIndex = find(id);
        models[arrayIndex].info = bytes.concat(models[arrayIndex].info, chunk);
    }

    // List all the models on the bbdd
    function read() view public returns(int[] memory, string[] memory) {
        return(ids, names);
    }

    // Download a model with an ID = id
    function loadConfig(int id) view public returns(int, bytes memory){
        uint arrayIndex = find(id);
        if(models[arrayIndex].model_type == 1){
            return (1, models[arrayIndex].info);
        }
        else if(models[arrayIndex].model_type == 2){
            return (2,models[arrayIndex].info);
        }
        else if(models[arrayIndex].model_type == 3){
            return (3,models[arrayIndex].info);
        }
        else{
            return (4, models[arrayIndex].info);
        }
    }

    // Find the model with ID = id, returns the position in the vector
    function find(int id) view internal returns(uint) {
        for(uint i = 0; i < models.length; i++) {
            if(models[i].id == id) {
                return (i);
            }
        }
        revert('Model does not exist!');
    }

    // Length of  the models array
     function length() view public returns(uint) {
        return models.length;
     }

}
