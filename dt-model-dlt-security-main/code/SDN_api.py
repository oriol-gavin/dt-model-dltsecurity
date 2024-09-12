from flask import Flask, request, jsonify

app = Flask(__name__)
sdni = None

@app.route('/DT_to_Controller', methods=['POST'])
def send_info_to_Controller():
    print("I'm the API sending info of the model to the Controller")
    model_info = request.json
    sdni.save_model(model_info)
    return jsonify({'message': "Model sent from the controller to the model manager"})

@app.route('/DLT_info', methods=['POST'])
def send_dlt_info_to_Controller():
    print("I'm the API sending info of the DLT to the Controller")
    model_info = request.json
    sdni.init_stats(model_info)
    return jsonify({'message': "Model sent from the controller to the model manager"})

def init(SDN):
    global sdni
    sdni = SDN
    app.run(debug=False, port=sdni.get_port_number())

    # endpoint for Controller to DT





