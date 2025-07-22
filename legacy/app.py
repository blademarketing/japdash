from flask import Flask, render_template, jsonify
import os
import requests
from dotenv import load_dotenv
from flask import request
import re



load_dotenv()

API_KEY = os.getenv("API_KEY")
API_URL = "https://justanotherpanel.com/api/v2"

app = Flask(__name__, static_url_path='/jap/static', static_folder='static')

def fetch_services():
    payload = {'key': API_KEY, 'action': 'services'}
    response = requests.post(API_URL, data=payload)
    return response.json()

@app.route('/jap/')
def index():
    return render_template('index.html')

@app.route('/jap/services')
def services():
    return jsonify(fetch_services())



@app.route('/jap/form-fields/<service_type>')
def form_fields(service_type):
    import json
    try:
        with open('services.json') as f:
            config = json.load(f)
    except FileNotFoundError:
        return jsonify([])

    print("REQUESTED TYPE:", service_type)
    print("AVAILABLE TYPES:", list(config.keys()))

    fields = config.get(service_type.strip())

    if not fields:
        # Try fallback: check if any key exists in service_type or service_name
        # service_name must be passed in the request for this to work
        service_name = request.args.get("service_name", "").lower()

        for key in config:
            if key.lower() in service_name:
                fields = config[key]
                break

    if not fields:
        fields = config.get("Default", [])

    return jsonify(fields)


@app.route('/jap/order', methods=['POST'])
def create_order():
    data = request.json
    payload = {'key': API_KEY, 'action': 'add'}
    payload.update(data)
    r = requests.post(API_URL, data=payload)
    return jsonify(r.json())




@app.route('/jap/ai-generate', methods=['POST'])
def ai_generate():
    import json
    from dotenv import load_dotenv
    load_dotenv()

    OPENAI_KEY = os.getenv('OPENAI_KEY')
    data = request.json
    ai_key = data.get('ai')
    target_field = data.get('target_field')
    form_data = data.get('form_data', {})

    def load_prompt(path):
        with open(path, encoding='utf-8') as f:
            return f.read()

    def replace_placeholders(text, data):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(data.get(m.group(1), "")), text)

    try:
        user_prompt = replace_placeholders(load_prompt(f'prompts/{ai_key}_user.txt'), form_data)
        system_prompt = replace_placeholders(load_prompt(f'prompts/{ai_key}_system.txt'), form_data)
    except FileNotFoundError:
        return jsonify({"error": "Prompt files not found"}), 400

    headers = {
        'Authorization': f'Bearer {OPENAI_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    res = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload)
    try:
        completion = res.json()['choices'][0]['message']['content']
    except:
        completion = '[Error parsing OpenAI response]'

    return jsonify({"field": target_field, "value": completion})


if __name__ == '__main__':    
    app.run(debug=True,port=9002)
