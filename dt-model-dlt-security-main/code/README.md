# Files
sequential: Model used in the demo

credentials.json: JSON file with the directions of the DLT. This file has no need to change it. The only case when it would be necessary to change it, it would be if we've had deployed the DLT not locally. If that's the case, we need to change the address from the nodes from 127.0.0.1:3334 to XXX.X.X.X:3334 where the XX are our new ip. 

DT.py: Code of the model manager. Once running, choose the port number (usually 5000, 5002, 5004,...), it must be unique

To run it: 
```bash
./DT.py
```
	
DT_api.py: Code of the API of the model manager. There is no need to run it ever, the DT does it itself
	  
MasContract.sol: Code of the Smart Contract. No need to run, the clients will reach it eventually when its necessary.
		
NetworkOrchestrator.py: Code of the Orchestrator of the connections. Once running, write the contract name (MasContract.sol) and it will start the execution based on the JSON files.

To run it:
```bash
./NetworkOrchestrator.py
```

ports_info.json: Information about the API ports used by the clients. We need to change it with the ports numbers chosen in the SDN and DT
		 
SDN_api.py: Code of the API of the Client-DLT-connection manager. No need to run, the SDN does it itself.
	   
SDN_Controller.py: Code of the Client-DLT-connection manager. Once running, choose the port for the API, (usually 5001, 5003, 5005,...), it must be unique

To run it:
```bash
./SDN.py
```

It's really important that the API ports follow the rule: SDN port is always one number more than the DT.

weights_pb2.py: Code necessary for the serialization. No need to run it
