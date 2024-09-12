from flask import Flask, request, jsonify

app = Flask(__name)

@app.route('/send_data', methods=['POST'])
def send_data():
    data = request.json  # Assuming data is sent as JSON
    result = agent.process_data(data)  # Send data to Agent for processing
    return jsonify({"message": "Data sent to Agent", "result": result})

if __name__ == '__main__':
    app.run()