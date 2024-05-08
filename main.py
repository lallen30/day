import logging
from flask import Flask, request, jsonify
import openai
from openai import OpenAI
import uuid
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os
import db

app = Flask(__name__)
# app.logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
# app.logger.addHandler(stream_handler)

db.init_db(app)

CORS(app, supports_credentials=True)
jwt = JWTManager(app)
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')

perplexity_api_key = None
openai_api_key = None

def initialize_clients():
    global perplexity_api_key, openai_api_key
    try:
        perplexity_api_key = db.get_api_key('PPLX_API_KEY')
        openai_api_key = db.get_api_key('OPENAI_API_KEY')
        if not perplexity_api_key or not openai_api_key:
            raise ValueError("API keys are not set in the database.")
    except Exception as e:
        # app.logger.error(f"Failed to initialize API clients: {str(e)}")
        raise

@app.after_request
def after_request_func(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    try:
        content = request.get_json()
        keys = content.get('keys', [])
        if not keys:
            return jsonify({'error': 'No keys provided'}), 400
        db_connection = db.get_db()
        cursor = db_connection.cursor()
        for key in keys:
            key_name = key.get('key_name')
            key_value = key.get('key_value')
            if not key_name or not key_value:
                return jsonify({'error': 'Missing key name or key value for some entries'}), 400

            # Insert or update the API key
            cursor.execute("""
                INSERT INTO api_keys (key_name, key_value)
                VALUES (?, ?)
                ON CONFLICT(key_name) DO UPDATE SET key_value = excluded.key_value;
            """, (key_name, key_value))
        db_connection.commit()

        # Initialize clients after updating keys
        initialize_clients()

        return jsonify({'message': 'API keys updated successfully.'})
    except Exception as e:
        # app.logger.error(f"Failed to set API keys: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/qna', methods=['POST'])
def chat():
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    if not perplexity_api_key or not openai_api_key:
        return jsonify({'error': 'API clients are not initialized'}), 500
    if check_question_stock_market(question):
        return query_perplexity_model(question)
    return jsonify({'message': 'Please keep questions related to the stock market'}), 400



def check_question_stock_market(question):
    openaiClient = OpenAI(api_key=openai_api_key)
    try:
        response = openaiClient.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI trained to discuss and analyze the stock market."},
                {"role": "user", "content": f"Is this question about the stock market? Yes or no: {question}"}
            ]
        )
        # Access the content directly from the response object
        answer = response.choices[0].message.content.strip().lower()
        
        if 'yes' in answer:
            return True
        elif 'no' in answer:
            return False
        else:
            # app.logger.debug(f"Unusual response from model: {answer}")
            return False

    except Exception as e:
        # app.logger.error(f"Error during model interaction: {str(e)}")
        return False



def query_perplexity_model(question):
    try:
        pplxClient = OpenAI(api_key=perplexity_api_key, base_url="https://api.perplexity.ai")

        messages = [
        {
            "role": "system",
            "content": "You are an artificial intelligence assistant specializing in the Stock Market."
        },
        {
            "role": "user",
            "content": question
        }
    ]

        response = pplxClient.chat.completions.create(
            model="pplx-70b-online",
            messages=messages
        )

        # app.logger.debug(response)
        
        # Check if the response has the necessary attributes
        if hasattr(response, 'choices') and response.choices:
            return jsonify(serialize_chat_completion(response))
        else:
            raise ValueError("Invalid response structure or missing data.")
    
    except Exception as e:
        # app.logger.error(f"Failed to query Perplexity model: {str(e)}")
        return jsonify({'error': str(e)}), 500



def serialize_chat_completion(response):
    # Assuming response.choices contains a list of Choice objects
    if response.choices:
        # Accessing the message content directly from the first choice
        choice = response.choices[0]
        message_content = choice.message.content  # Direct attribute access
        question_session_id = str(uuid.uuid4())  # Generate a unique session ID

        return {
            'answer': message_content,
            'question': "Question not directly available",  # Since it seems you can't fetch it directly
            'question_session_id': question_session_id
        }
    else:
        return {'error': 'No choices available in the response.'}



@app.route('/test_connection', methods=['GET'])
def test_connection():
    return jsonify({'message': 'Connection to API successful', 'OPENAI_API_KEY': openai_client.api_key if openai_client else None, 'PERPLEXITY_API_KEY': perplexity_client.api_key if perplexity_client else None}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
