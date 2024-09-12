import json
import random
import requests
import solcx
import time as t
from web3 import Web3
from web3.middleware import geth_poa_middleware
from solcx import compile_standard

import ast


# APROFITAR FUNCIONS DE MLFO i DLTManager PER OMPLIR AQUEST

class NetworkOrchestrator():
    def __init__(self, sdn_ports, dt_ports):

        self.sdn_ports = sdn_ports
        self.dt_ports = dt_ports
        with open('credentials.json', 'r') as json_file:
            info = json.load(json_file)
        self.eth_nodes = info["eth_nodes"]
        self.eth_address = info["eth_address"]
        self.private_key = info["private_key"]
        self.chain_id = info["chain_id"]
        self.agent_names = info["agent_names"]
        self.contract_name = ""
        self.accounts = []
        self.contract_address = None
        self.contract_abi = None
        self.contract = None
        self.contract_deployed = False
        self.agents_registered = None
        self.key_set = False
        try:
            self.web3 = Web3(Web3.WebsocketProvider(self.eth_nodes[1]))
        except:
            raise Exception("Web3 connection failed")
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        try:
            self.nonce = self.web3.eth.getTransactionCount(self.eth_address)
        except:
            raise Exception("DLT connection failed")

    def deploy_contract(self, contract_path):
        # Function to deploy the contract to the DLT.
        with open(contract_path, "r") as file:
            contact_list_file = file.read()

        compiled_sol = compile_standard(
            {
                "language": "Solidity",
                "sources": {contract_path: {"content": contact_list_file}},
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
        self.contract_name = contract_path.split(".")[0]
        bytecode = compiled_sol["contracts"][contract_path][self.contract_name]["evm"]["bytecode"]["object"]
        self.contract_abi = \
            json.loads(compiled_sol["contracts"][contract_path][self.contract_name]["metadata"])["output"]["abi"]
        Contract = self.web3.eth.contract(abi=self.contract_abi, bytecode=bytecode)
        self.nonce = self.web3.eth.getTransactionCount(self.eth_address)
        transaction = Contract.constructor().buildTransaction(
            {"chainId": self.chain_id, "gasPrice": self.web3.eth.gas_price, "from": self.eth_address,
             "nonce": self.nonce}
        )
        sign_transaction = self.web3.eth.account.sign_transaction(transaction, private_key=self.private_key)
        transaction_hash = self.web3.eth.send_raw_transaction(sign_transaction.rawTransaction)
        transaction_receipt = self.web3.eth.wait_for_transaction_receipt(transaction_hash)
        self.contract_address = transaction_receipt.contractAddress
        self.contract = self.web3.eth.contract(abi=self.contract_abi, address=self.contract_address)

    def import_and_unlock_accounts(self, accounts, names):
        # Function to import and unlock accounts using their private keys
        for i in range(len(accounts)):
            private_key = accounts[names[i]]['private_key']
            decrypted_account = self.web3.eth.account.privateKeyToAccount(private_key)
            try:
                self.web3.geth.personal.import_raw_key(private_key, "")
                self.web3.geth.personal.unlock_account(decrypted_account.address, "")
                print(f"Successfully unlocked account {decrypted_account.address}")
            except Exception as e:
                print(f"An error occurred while unlocking account {decrypted_account.address}: {e}")

    def create_account_and_fund(self, names, value_ether=0.05):
        # Function to create the clients accounts and give them al the necesary information
        accounts = {}
        print(len(names))
        for i in range(len(names)):
            account = self.web3.eth.account.create()
            accounts[str(names[i])] = {
                'name': names[i],
                'address': account.address,
                'private_key': account.privateKey.hex()[2:],  # Remove the "0x" prefix from the private key
                'balance': self.web3.eth.get_balance(account.address)
            }

        # Import and unlock the accounts
        self.import_and_unlock_accounts(accounts, names)

        # Now, let's fund the new accounts from the pre-funded address
        from_address = self.web3.eth.accounts[0]  # Assuming the pre-funded address is the first account
        value_wei = self.web3.toWei(value_ether, "ether")

        for i in range(len(names)):
            to_address = accounts[names[i]]['address']
            self.web3.eth.send_transaction({
                'from': from_address,
                'to': to_address,
                'value': value_wei
            })

        # Add a delay to allow time for transactions to be processed
        t.sleep(3)

        # Now, let's fetch and update the balances after the transfers
        for i in range(len(names)):
            accounts[names[i]]['balance'] = self.web3.eth.get_balance(accounts[names[i]]['address'])
            accounts[names[i]]['eth_node'] = random.choice(self.eth_nodes)
            accounts[names[i]]['contract_address'] = self.contract_address
            accounts[names[i]]['eth_address'] = self.eth_address

        return accounts  # En lloc de ser una llista podria ser millor un diccionari nom -> info, on el nom es name, i info es la resta de coses de la llista

    def request_dlt_addresses(self, agent_names):
        # Function that returns the created accounts based on the agent names
        accounts = self.create_account_and_fund(agent_names)
        return accounts

    def send_signed_transaction(self, build_transaction):
        # Function to send a transaction but signed with a secret key

        # Sign the transaction
        try:
            signed_txn = self.web3.eth.account.signTransaction(build_transaction, self.private_key)
        except:
            raise Exception("Couldn't signt the transaction" + str(build_transaction))
        # Send the signed transaction
        try:
            tx_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
        except:
            raise Exception("Error sendind the transaction")
        # Increment the nonce
        self.nonce += 1

        return tx_hash

    def register_agents(self, accounts, names):
        # Function to add the accounts information to the Smart Contract so that they can actually use it

        agent_addresses = []
        agent_names = []
        self.nonce = self.web3.eth.getTransactionCount(self.eth_address)
        for i in range(len(accounts)):
            agent_addresses.append(accounts[names[i]]["address"])
            agent_names.append(names[i])
        try:
            tx_data = self.contract.functions.registerAgents(
            agent_addresses,
            agent_names
            ).buildTransaction({'from': self.eth_address, 'nonce': self.nonce})
        except:
            raise Exception("Couldn't build the Register Agents transaction")

        # Send the signed transaction
        self.send_signed_transaction(tx_data)

    def unregister_agents(self, accounts, names):
        # Function to unregister agents from the Smart Contract so that they can't use it

        agent_addresses = []
        agent_names = []
        self.nonce = self.web3.eth.getTransactionCount(self.eth_address)
        for i in range(len(accounts)):
            agent_addresses.append(accounts[names[i]]["address"])
            agent_names.append(accounts[names[i]]["name"])
        try:
            tx_data = self.contract.functions.unregisterAgents(
            agent_addresses,
            agent_names
            ).buildTransaction({'from': self.eth_address, 'nonce': self.nonce})
        except:
            raise Exception("Couldn't build the Unregister Agents transaction")
        # Send the signed transaction
        self.send_signed_transaction(tx_data)

    def delete_agents(self, accounts, names):
        # Function to delete from the DLT the client. Not used, it better to just unregister

        agent_addresses = []
        agent_names = []
        self.nonce = self.web3.eth.getTransactionCount(self.eth_address)
        for i in range(len(accounts)):
            agent_addresses.append(accounts[names[i]]["address"])
            agent_names.append(accounts[names[i]]["name"])
        try:
            tx_data = self.contract.functions.deleteAgents(
            agent_addresses,
            agent_names
            ).buildTransaction({'from': self.eth_address, 'nonce': self.nonce})
        except:
            raise Exception("Couldn't build the Delete Agents transaction")

        # Send the signed transaction
        self.send_signed_transaction(tx_data)

    def automatic_start(self):
        # Function that does all the basics to be able to connect clients and DLT
        txt = "Please enter contract path: "
        try:
            self.contract_name = input(txt)
            self.deploy_contract(self.contract_name)
        except:
            raise Exception("ERROR: No Smart Contract found with that name")
        try:
            self.accounts = self.request_dlt_addresses(self.agent_names)
            print(self.accounts)
        except:
            raise Exception("ERROR: Couldn't create the clients")
        try:
            self.register_agents(self.accounts, self.agent_names)
        except:
            raise Exception("ERROR: Couldn't Register the clients")

        for i in range(len(self.accounts)):
            self.accounts[self.agent_names[i]]["contract_name"] = self.contract_name

        for i in range(len(self.accounts)):
            data_to_send = self.accounts[self.agent_names[i]]
            try:
                response = requests.post('http://localhost:' + str(self.sdn_ports[i]) + '/DLT_info',
                                     json=data_to_send)
            except:
                raise Exception("Error connecting with SDN API")

    def run(self):
        if (len(self.sdn_ports) != len(self.agent_names)):
            print("Diferent ports than names")
        else:
            print("Connecting with DLT...")
            self.automatic_start()
            print("Connected, if needed you can do it again: ")
            while True:
                menu = """Please select one of the following options:
                1) Compile and deploy contract on DLT
                2) Request N addresses for the agents
                3) Register the agents in the DLT
                4) Distribute SmartContract Details to nodes
                5) Send info to actual clients
                6) Unregister agents in the DLT
                7) Delete agents in the DLT
                8) Ask DT to upload a model
                9) Ask DT to unserialize the model
                10) Exit
                Your selection: """
                welcome = "MLFO"

                print(welcome)

                while (user_input := input(menu)) != "10":
                    if user_input == "1":
                        txt = "Please enter contract path: "
                        self.contract_name = input(txt)
                        self.deploy_contract(self.contract_name)
                        print(self.contract_name)
                        self.contract_deployed = True
                    elif user_input == "2":
                        if self.contract_deployed:
                            self.accounts = self.request_dlt_addresses(self.agent_names)
                            print(self.accounts)
                        else:
                            print("Can't request DLT addresses: Contract not deployed!")
                    elif user_input == "3":
                        if self.accounts is not None:
                            self.register_agents(self.accounts, self.agent_names)
                            self.agents_registered = True
                        else:
                            print("Can't unlock addresses: DLT addresses not available!")
                    elif user_input == "4":
                        if self.agents_registered:
                            for i in range(len(self.accounts)):
                                self.accounts[self.agent_names[i]]["contract_name"] = self.contract_name
                                print(self.accounts[self.agent_names[i]]["contract_name"])
                        else:
                            print("Can't distribute addresses: DLT addresses not unlocked!")

                    elif user_input == "5":
                        if self.agents_registered:
                            for i in range(len(self.accounts)):
                                data_to_send = self.accounts[self.agent_names[i]]
                                response = requests.post('http://localhost:' + str(self.sdn_ports[i]) + '/DLT_info',
                                                         json=data_to_send)
                                # print(response.json())
                    elif user_input == "6":
                        if self.agents_registered:
                            self.unregister_agents(self.accounts, self.agent_names)
                        else:
                            print("Key is not set yet!")
                    elif user_input == "7":
                        if self.agents_registered:
                            self.delete_agents(self.accounts, self.agent_names)
                    elif user_input == "8":
                        dt_port = input("Please choose a DT from " + str(self.dt_ports) + ": ")
                        response = requests.post('http://localhost:' + dt_port + '/send_model')
                    else:
                        print("Invalid option, please try again!")


if __name__ == "__main__":
    solcx.install_solc('0.8.12')
    with open('ports_info.json', 'r') as json_file:
        info = json.load(json_file)

    SDN_ports = info["SDN_ports"]
    DT_ports = info["DT_ports"]
    no = NetworkOrchestrator(SDN_ports,DT_ports)
    no.run()
