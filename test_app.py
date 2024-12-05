from flask import Flask, render_template
import os

app = Flask(__name__, 
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
)

@app.route('/')
def home():
    return "Home page works!"

@app.route('/study_guide')
def study_guide():
    print("\n\n=== Accessing study_guide route ===")
    try:
        print("Debug: Entering study_guide route")
        print(f"Debug: Current working directory: {os.getcwd()}")
        print(f"Debug: Template folder is {app.template_folder}")
        print(f"Debug: All template files: {os.listdir(app.template_folder)}")
        template_path = os.path.join(app.template_folder, 'study_guide_test.html')
        print(f"Debug: Full template path is {template_path}")
        print(f"Debug: Template exists? {os.path.exists(template_path)}")
        
        if not os.path.exists(template_path):
            error_msg = f"Template file not found at {template_path}"
            print(f"Debug: {error_msg}")
            return error_msg, 404
            
        print("Debug: Template file exists, attempting to render")
        result = render_template('study_guide_test.html')
        print("Debug: Successfully rendered template")
        return result
        
    except Exception as e:
        error_msg = f"Error in study_guide route: {str(e)}"
        print(f"Debug: {error_msg}")
        return error_msg, 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
