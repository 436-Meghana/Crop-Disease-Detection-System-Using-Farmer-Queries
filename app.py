from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from PIL import Image
import json
import os

app = Flask(__name__)
# Enable CORS so the local frontend HTML file can communicate with this backend server
CORS(app)

# ==============================================================================
# SECURE CLOUD DEPLOYMENT: Read API Key from Environment Variables
# ==============================================================================
API_KEY = os.environ.get('GEMINI_API_KEY')

# Configure the Gemini API network
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    print("WARNING: GEMINI_API_KEY environment variable not found!")

# Define the strict instructions for the AI on how to format its output
SYSTEM_INSTRUCTION = """
You are an expert agronomist and plant pathologist. 
You will be provided with an image of a plant leaf and/or a text query from a farmer.
Your job is to identify the disease accurately (e.g. Cuckoo Spit, Powdery Mildew, Leaf Blight) and provide an actionable, recommended solution.

CRITICAL: You MUST respond ONLY with a raw JSON object and nothing else. No markdown formatting, no backticks.
The JSON must strictly follow this exact structure:
{
    "disease": {
        "en": "Disease name in English",
        "hi": "Disease name in Hindi",
        "kn": "Disease name in Kannada",
        "te": "Disease name in Telugu",
        "ml": "Disease name in Malayalam",
        "ta": "Disease name in Tamil"
    },
    "solution": {
        "en": "Solution in English",
        "hi": "Solution in Hindi",
        "kn": "Solution in Kannada",
        "te": "Solution in Telugu",
        "ml": "Solution in Malayalam",
        "ta": "Solution in Tamil"
    }
}
"""

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/')
def serve_index():
    # Serve index.html from the absolute parent folder (CropDiseaseDetector)
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    # Serve css and js files from the absolute parent folder
    return send_from_directory(BASE_DIR, filename)


    try:
        # 2. Extract the data sent securely by the frontend JavaScript
        uploaded_file = request.files.get('image')
        query_text = request.form.get('queryText', '')

        # 3. Setup Gemini AI Model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 4. Prepare the Multimodal Data for the Model
        contents = [SYSTEM_INSTRUCTION]
        
        if query_text:
            contents.append(f"Farmer Query: {query_text}")
            
        if uploaded_file and uploaded_file.filename != '':
            # Convert the uploaded file directly into a visual PIL Image for Gemini to 'see'
            img = Image.open(uploaded_file.stream)
            contents.append(img)
            
        if not query_text and (not uploaded_file or uploaded_file.filename == ''):
            return jsonify({"status": "error", "message": "No image or query provided."}), 400

        # 5. Send the Image and Text directly to Google Gemini for processing!
        response = model.generate_content(contents)
        
        # 6. Parse the JSON response returned by the AI
        raw_text = response.text.strip()
        
        # Clean up any markdown blocks if Gemini formats it as a codeblock
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "", 1)
        if raw_text.endswith("```"):
            raw_text = raw_text[::-1].replace("```", "", 1)[::-1]
            
        result_json = json.loads(raw_text.strip())

        # 7. Send the real AI data back to your local website browser!
        return jsonify({
            "status": "success",
            "result": result_json
        }), 200

    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": error_msg
        }), 500

if __name__ == '__main__':
    # Starts the local development server at http://127.0.0.1:5000/
    app.run(debug=True, port=5000)
