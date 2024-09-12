import threading
import requests
from web3 import Web3
import json
import SDN_api
import ast
import time
from solcx import compile_standard
from web3.middleware import geth_poa_middleware



class SDN_Controller:
    def __init__(self, portnumber):
        #Inicialization of parameters, most of them are filled with the Network Orchestrator information
        self.port_num = int(portnumber)
        self.nonce = None
        self.private_key = None
        self.eth_address = None
        self.web3_adress = None
        self.web3 = None
        # Aquí el parametre serà self.web3_adress, que vindrà donat d'un arxiu de configuració

        self.contract_abi = None
        # Aquí realment el json que carrgaré serà el que rebre de rebre un POST del Orchestrator

        self.contract_address = None
        # Aquesta adreça també es rebrá en el POST del Orchestrator
        self.contract_name = None
        self.contract_path = None
        self.my_contract = None
        self.eth_address = None
        # La eth_adress també la sabré ja en el fitxer config, no haure de carregar totes

        self.chunk_size_kb = 8
        self.chunk_size_bytes = self.chunk_size_kb * 1024

        self.model_to_send = None
        self.model_type = None
        self.model_to_send_ready = False
        self.not_sending = True
        ##FUNCTIONS

    def send_signed_transaction(self, build_transaction):
        # Sign the transaction
        try:
            signed_txn = self.web3.eth.account.signTransaction(build_transaction, self.private_key)
        except:
            raise Exception("Couldn't sign the transaction" + str(build_transaction))
        # Send the signed transaction
        try:
            tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        except:
            raise Exception("Couldn't send the transaction")
        # Increment the nonce
        self.nonce += 1

        return tx_hash
    def transact_model(self, input, info,
                       type):
        # This function recieves some input, some information and a type of information to send to the SC

        try:
            tx_data = self.my_contract.functions.addModelSerialized(self.eth_address, input, info, type).buildTransaction({'from': self.eth_address, 'nonce': self.nonce})
        except:
            print("Couldn't build the transaction")
            tx_data = None
        if tx_data is not None:
            self.send_signed_transaction(tx_data)
            print("\n(Transaction) : New model added")

    def get_block_events(self, latestblock):
        # Ths function gets a new block from the blockchain and gets some of its information
        try:
            block = self.web3.eth.getBlock('latest')
        except:
            #print("Unable to check the last block, trying again in 5 seconds")
            block = None
        if block is not None:
            blocknumber = block['number']
        else:
            blocknumber = None
        if blocknumber is not None and blocknumber != latestblock:
            #print("\nLatest block:", blocknumber)
            latestblock = blocknumber
            event_filter = self.my_contract.events.NewModel.createFilter(fromBlock=self.web3.toHex(blocknumber))
            return event_filter, latestblock
        return None, latestblock

    def wait_for_models(self):
        # Blocking function that waits for models from other clients. It is running in parallel.
        latestblock = -1
        print("I'm waiting for models")
        while True:
            time.sleep(0.01)  # Aquest time fa que no peti dues crides a l'hora al DLT
            if self.not_sending:
                #print("trying")
                block_events, latestblock = self.get_block_events(latestblock)

                # Wait for the MLFO to set a new secret key
                if block_events is not None:
                    #print("New block")
                    new_events = block_events.get_all_entries()
                    for event in new_events:
                        print("New event")
                        info = dict(dict(event)['args'])
                        # Amb el que tenim a info caldrà fer un POST AL DT

                        data_to_send = {'model': str(info["model"]), 'model_type': info["modelType"]}
                        try:
                            response = requests.post('http://localhost:' + str(self.port_num - 1) + '/Controller_to_DT', json=data_to_send)
                        except:
                            raise Exception("Couldn't comunicate with the DT API")
                        break
    def save_model(self, model):
        # Gets the model from the DT and saves it

        print("I've recieved a model from the DT")
        self.model_to_send = ast.literal_eval(model["model_info"])
        self.model_type = model["model_type"]
        #self.transact_model("Model name", self.model_to_send, self.model_type)
        self.model_to_send_ready = True

    def init_stats(self, info):
        # Inicialization of the parameters given by the Network Orchestrator

        print("I'm in the SDN, this is what i've received: " + str(info))
        self.private_key = info['private_key']
        self.eth_address = info['address']
        try:
            self.web3 = Web3(Web3.WebsocketProvider(info['eth_node']))
        except:
            raise Exception("Communication with Web3 went wrong")
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract_path = info["contract_name"] + ".sol"
        self.contract_name = info["contract_name"]
        abi_path = ""#info['path']
        with open(abi_path+self.contract_path, "r") as file:
            contact_list_file = file.read()
        compiled_sol = compile_standard(
            {
                "language": "Solidity",
                "sources": {self.contract_path: {"content": contact_list_file}},
                "settings": {
                    "outputSelection": {
                        "*": {
                            "*": ["abi", "metadata", "evm.bytecode", "evm.bytecode.sourceMap"]
                        }
                    }
                },
            },
            solc_version="0.8.12",
        )
        self.contract_abi = json.loads(compiled_sol["contracts"][self.contract_path][self.contract_name]["metadata"])["output"]["abi"]

        self.contract_address = Web3.to_checksum_address(info['contract_address'])
        self.my_contract = self.web3.eth.contract(abi=self.contract_abi, address=self.contract_address)

        self.nonce = self.web3.eth.getTransactionCount(self.eth_address)

        process2 = threading.Thread(target=SDN_Controller.wait_for_models, name="Event_listener")
        process2.start()

    def run(self):
        # Wait until a model is ready to be sent, send it then
        while True:
            if self.model_to_send_ready:
                self.not_sending = False
                time.sleep(0.01) # Time.sleep to not overwhelm the SDN
                self.transact_model("Model name", self.model_to_send, self.model_type)
                self.not_sending = True
                self.model_to_send_ready = False

    def get_port_number(self):
        return self.port_num

if __name__ == "__main__":
    inp = input("Choose the port number: ")
    SDN_Controller = SDN_Controller(inp)
    # Proces paralel per a la API
    process1 = threading.Thread(target=SDN_api.init, args=(SDN_Controller,), name="SDN_api_thread")
    process1.start()


    SDN_Controller.run()
    # 1 process per la API, crear instancia, fer run
    # POST a la api indicant
