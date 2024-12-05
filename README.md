# AI Tutor - Homework Helper

An intelligent educational application that helps students learn by providing guided assistance with their homework. The application uses AI to analyze homework problems, generate similar practice problems, and provide detailed feedback without giving away direct answers.

## Features

1. **Practice Problems Generator**
   - Upload homework questions via image
   - AI analyzes the problem type
   - Generates similar practice problems
   - Provides step-by-step guidance

2. **Homework Checker**
   - Upload completed homework
   - AI verifies solutions
   - Detailed feedback on correctness
   - Learning suggestions and tips

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   python app.py
   ```

## Usage

1. Open your web browser and navigate to `http://localhost:5000`
2. Upload a homework problem image to get similar practice problems
3. Use the homework checker to verify your solutions
4. Follow the AI's guidance to improve your understanding

## Technical Stack

- Backend: Flask (Python)
- Frontend: HTML, CSS (Tailwind), JavaScript
- AI/ML: Transformers, OpenCV
- Image Processing: PIL, NumPy

## Future Enhancements

- Subject-specific tutoring modes
- Progress tracking
- Personalized learning paths
- Parent/teacher dashboard
- Gamification elements
- Multi-language support

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
