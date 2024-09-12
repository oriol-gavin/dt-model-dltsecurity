# Import the necessary classes and functions from the web3 library for interacting with the blockchain network.
import numpy as np
import json
import keras
import pickle
import ast
import time
import msgpack
import lzma
from keras.models import load_model
from tensorflow.keras.layers import Input, Dense
import weights_pb2
import requests
import DT_api
import threading

# This class implements the Digital Twin of a model
class DT:
    def __init__(self, portnumber):
        #Inicialization of the model information
        self.port_number = int(portnumber)
        self.model_type = None
        self.model_received = False
        self.models = []
        self.model_to_send = load_model('sequential')
        self.config = self.model_to_send.get_config()
        self.simple_config = self.simplify_config(self.config)  # Simplify the model configuration
        self.weights_matrix = self.model_to_send.get_weights()
        self.flat_matrix = self.matrix_flat(self.weights_matrix)  # Flatten the weight matrix

    def simplify_config(self,
                        config):
        # This function recieves a model config and converts it into a simplified one (we assume always same structure)
        config_simple = []
        layers = config["layers"]
        layer_name_input = layers[0]["class_name"]
        layer_size_input = layers[0]["config"]["batch_input_shape"][1]
        config_simple.append({"name": layer_name_input, "size": layer_size_input})
        for i in range(1, len(layers)):
            layer_name = layers[i]["class_name"]  # Nombre capa
            layer_size = layers[i]["config"]["units"]  # Tamaño capa
            layer_activation = layers[i]["config"]["activation"]
            config_simple.append({"name": layer_name, "size": layer_size, "activation": layer_activation})
        return {"layers": config_simple}

    def matrix_flat(self, matrix):
        # This function recieves a matrix and flattens it
        list = []
        for m in matrix:
            list.extend(m.flatten())
        return list

    def deserialize_weights(self, weights,
                            config):
        # This function recieves a flattened list of floats and a model config and it converts the list into a matrix that the model creator understands
        w = np.array(weights, dtype=np.float32)
        final_weight = []
        for i in range(len(config["layers"]) - 1):
            size_from = config["layers"][i]["size"]
            size_to = config["layers"][i + 1]["size"]
            layer_weights = []
            for j in range(size_from):
                neuron, w = w[:size_to], w[size_to:]
                layer_weights.append(neuron)
            final_weight.append(np.array(layer_weights, dtype=np.float32))
            bias, w = w[:size_to], w[size_to:]
            final_weight.append(np.array(bias, dtype=np.float32))
        return final_weight

    def deserialize_model(self, config_type, config_info):
        # Function to deserialize a model and actually build a neural network
        if config_type == 1:  # Here I have bytes that correspond to a whole model, serialized with pickle
            model_info = pickle.loads(config_info)
            model_info.summary()
        elif config_type == 2:  # Here I have bytes corresponding to a dictionary with config and weights, serialized with msgpack
            model_info = msgpack.unpackb(config_info)
            m2 = keras.Sequential.from_config(model_info['config'])
            loaded_weights = self.deserialize_weights(ast.literal_eval(model_info["weights"]),
                                                      self.simplify_config(model_info['config']))
            m2.set_weights(loaded_weights)
            m2.summary()
        elif config_type == 3:  # Here I have bytes corresponding to a dictionary with the simplified config and weights, serialized  with msgpack
            model_info = msgpack.unpackb(config_info)
            config_data = model_info["config"]
            m2 = keras.Sequential()
            for layer_data in config_data["layers"]:
                if layer_data['name'] == 'InputLayer':
                    m2.add(Input(shape=(layer_data['size'],)))
                elif layer_data['name'] == 'Dense':
                    m2.add(Dense(layer_data['size'], activation=layer_data['activation']))
            loaded_weights = self.deserialize_weights(ast.literal_eval(model_info["weights"]), config_data)
            m2.set_weights(loaded_weights)
            m2.summary()
        else:  # Here I have bytes corresponding to a dictionary with the simplified config and weights, serialized  with grpc
            deserialized_model = weights_pb2.Model()
            deserialized_model.ParseFromString(config_info)
            weights_data = list(deserialized_model.weights)
            m2 = keras.Sequential()
            for layer_data in deserialized_model.layers:
                if layer_data.name == 'InputLayer':
                    m2.add(Input(shape=(layer_data.size,)))
                elif layer_data.name == 'Dense':
                    m2.add(Dense(layer_data.size, activation=layer_data.activation))

            # Rebuild the weights in a understandable format
            w = np.array(weights_data, dtype=np.float32)
            loaded_weights = []
            for i in range(len(deserialized_model.layers) - 1):
                size_from = deserialized_model.layers[i].size
                size_to = deserialized_model.layers[i + 1].size
                layer_weights = []
                for j in range(size_from):
                    neuron, w = w[:size_to], w[size_to:]
                    layer_weights.append(neuron)
                loaded_weights.append(np.array(layer_weights, dtype=np.float32))
                bias, w = w[:size_to], w[size_to:]
                loaded_weights.append(np.array(bias, dtype=np.float32))

            # We add the weights to the model
            m2.set_weights(loaded_weights)
            m2.summary()
            self.models.append(m2)
            self.model_received = None
            self.model_type = None

    def save_model(self, model_info):
        # Given some bytes, they are decompressed into information that can be stored are read
        print("Model received")
        self.model_received = lzma.decompress(ast.literal_eval(dict(model_info)["model"]))
        self.model_type = int(dict(model_info)["model_type"])
        self.deserialize_model(self.model_type, self.model_received)


    def get_port_number(self):
        return self.port_number

    def send_model(self):
        # Function to send the model to the SDN via method number 4 -> GRPCD serialization + lzma compression

        debug_txt = "model"  # input("Enter the name of the new model: ")
        aux = weights_pb2.Model()
        # Config addition to grpc
        model_bytes = None
        for layer in self.simple_config['layers']:
            l = aux.layers.add()
            l.name = layer["name"]
            l.size = layer["size"]
            if layer['name'] == "InputLayer":
                l.activation = 'linear'
            else:
                l.activation = layer['activation']
                # Weights addition to grpc
                for w in self.flat_matrix:
                    aux.weights.append(w)
        model_bytes = aux.SerializeToString()  # Serialize the model using GRPC
        model_bytes = lzma.compress(model_bytes)
        print("Size of the model using protobuffer to serialize is: " + str(len(model_bytes)) + " bytes" + "\n")
        # Send a post method to the SDN API
        data_to_send = {'model_info': str(model_bytes), 'model_type': 4}
        try:
            response = requests.post('http://localhost:' + str(self.port_number + 1) + '/DT_to_Controller',
                                 json=data_to_send)
        except:
            raise Exception("Error communicating with SDN API")


    def run(self):
        while True:
            print("\n")
            print("+----------------------------------------------------+")
            print("|  1. Send a model serialized                        |")
            print("|  2. Send a model with default config               |")
            print("|  3. Send a model with simple config                |")
            print("|  4. Send a model with simple config and using grpc |")
            print("|  5. Deserialize the model recieved                 |")
            print("|  6. Exit                                           |")
            print("+----------------------------------------------------+")
            choice = input("Enter your choice (1-6): ")
            print("\n")
            if choice == "1":
                # Option to send the whole model to the SDN
                debug_txt = "Model"  # input("Enter the name of the new model: ") #Asks for a model name
                model_bytes = pickle.dumps(self.model_to_send)  # Serialize the whole model with pickle library
                model_bytes = lzma.compress(model_bytes)
                print("\nSize of the whole model serialized in bytes with pickle all at once is " + str(
                    len(model_bytes)) + " bytes" + "\n")
                # Send a post method to Controller
                data_to_send = {'model_info': str(model_bytes), 'model_type': 1}
                try:
                    response = requests.post('http://localhost:' + str(self.port_number + 1) + '/DT_to_Controller',
                                         json=data_to_send)
                except:
                    raise Exception("Error communicating with SDN API")

            elif choice == "2":  # CONFIG AND WEIGHTS ONLY
                # Option to send the model using normal config and weights matrix
                debug_txt = input("Enter the name of the new model: ")
                model_info = {"config": self.config, "weights": str(
                    self.flat_matrix)}  # We create a matrix with the relevant info of the model
                model_bytes = msgpack.packb(model_info)  # Serialize the dictionary with msgpack library
                model_bytes = lzma.compress(model_bytes)
                print(
                    "Size of the model dividing the config and the weights serialized to bytes is: " + str(
                        len(model_bytes)) + " bytes" + "\n")
                # Send a post method to Controller
                data_to_send = {'model_info': str(model_bytes), 'model_type': 2}
                try:
                    response = requests.post('http://localhost:' + str(self.port_number + 1) + '/DT_to_Controller',
                                         json=data_to_send)
                except:
                    raise Exception("Error communicating with SDN API")

            elif choice == "3":  # SIMPLE CONFIG AND WEIGHTS ONLY
                # Option to send the model using the simplificated version of the config file

                debug_txt = input("Enter the name of the new model: ")
                model_info = {"config": self.simple_config, "weights": str(
                    self.flat_matrix)}  # We create a matrix with the relevant info of the model simplified
                model_bytes = msgpack.packb(model_info)  # Serialize the dictionary with msgpack library
                model_bytes = lzma.compress(model_bytes)
                # Send a post method to Controller
                data_to_send = {'model_info': str(model_bytes), 'model_type': 3}
                try:
                    response = requests.post('http://localhost:' + str(self.port_number + 1) + '/DT_to_Controller',
                                         json=data_to_send)
                except:
                    raise Exception("Error communicating with SDN API")

            elif choice == "4":  # SIMPLE CONFIG AND WEIGHTS ONLY USING GRPC
                self.send_model()

            elif choice == "5":
                #Deserialize a model previously recieved
                if self.model_received is not None:
                    self.deserialize_model(self.model_type, self.model_received)
                else:
                    print("Model not recieved yet")
            elif choice == "6":
                break


if __name__ == "__main__":
    inp = input("Choose port number: ")
    d = DT(inp)

    process1 = threading.Thread(target=DT_api.init, args=(d,))
    process1.start()
    time.sleep(0.2)
    d.run()
