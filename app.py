from flask import Flask, request, jsonify
import json
from openai import AzureOpenAI
from flasgger import Swagger, swag_from
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS  # Import CORS

# Initialize Azure OpenAI
llm = AzureOpenAI(
    azure_endpoint="https://genral-openai.openai.azure.com/",
    api_key="8929107a6a6b4f37b293a0fa0584ffc3",
    api_version="2024-02-01"
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # This will allow cross-origin requests to all routes

# Swagger UI setup
SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = '/static/swagger.json'  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
    API_URL,
    config={  # Swagger UI config overrides
        'app_name': "AutoML APIs"
    }
)

app.register_blueprint(swaggerui_blueprint)

# Swagger configuration
swagger = Swagger(app, template={
    "info": {
        "title": "AutoML APIs",
        "description": "API for Automated Machine Learning tool",
        "version": "1.0.0"
    },
    "host": "reportdetailsapi-ecepdycjh4ekhsbr.eastus-01.azurewebsites.net",  # Change to your host if needed
    "basePath": "/",  # Base path for API
})

@app.route('/edit-arabic-report', methods=['POST'])
def edit_arabic_report():
    """
    API endpoint to edit an Arabic report JSON using a GPT-4o-generated response.

    Request Body:
        json_input (str): JSON-formatted string input.
        arabic_prompt (str): Arabic prompt describing the edits to apply.

    Returns:
        dict: The updated JSON structure.
    """
    try:
        # Parse input JSON from the request
        data = request.get_json()

        json_input_string = data.get('json_input')
        arabic_prompt = data.get('arabic_prompt')

        if not json_input_string or not arabic_prompt:
            return jsonify({"error": "Both 'json_input' and 'arabic_prompt' are required."}), 400

        # Parse the input JSON string into a Python dictionary
        try:
            input_json = json.loads(json_input_string)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format in 'json_input'."}), 400

        # Construct the GPT-4o input prompt
        conversation_history = [
        {
            "role": "system",
            "content": """You are a professional journalist proficient in Arabic.
                          You will edit the provided JSON structure to improve clarity, add details,
                          and make the content more engaging and comprehensive. Return the output as valid JSON."""
        },
        {"role": "user", "content": f"قم بتحسين هذا التقرير JSON بناءً على التعديلات التالية:\n{arabic_prompt}\n\nJSON الحالي:\n{json.dumps(input_json, ensure_ascii=False, indent=2)}"}
    ]


        # Call GPT-4o API to generate the updated content
        try:
            response = llm.chat.completions.create(
                model="gpt-4o",
                messages=conversation_history
            ).choices[0].message.content
        except Exception as api_error:
            return jsonify({"error": f"Failed to call Azure OpenAI API: {str(api_error)}"}), 500

        print("Raw response:", response)

        # Extract the content from the GPT response
        cleaned_response = response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[len('```json'):].strip()
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3].strip()

        # Parse the GPT output to JSON
        try:
            updated_json = json.loads(cleaned_response)
        except json.JSONDecodeError:
            return jsonify({"error": "GPT response is not a valid JSON."}), 500

        # Return the updated JSON
        return jsonify({"updated_json": updated_json}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/")
def hello_world():
    return "<p>Let's Update the heading!</p>"

if __name__ == '__main__':
    app.run(debug=True)
