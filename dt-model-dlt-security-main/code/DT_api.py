from flask import Flask, request, jsonify

app = Flask(__name__)
dti = None

@app.route('/Controller_to_DT', methods=['POST'])
def send_info_to_DT():
    print("API: sending info to the DT")
    model_info = request.json
    dti.save_model(model_info)
    return jsonify({'message': "Model sent from the controller to the model manager"})

@app.route('/send_model', methods=['POST'])
def upload_model():
    print("API: Sending model")
    dti.send_model()

def init(DT):
    global dti
    dti = DT
    app.run(debug=False, port=dti.get_port_number())

