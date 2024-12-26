# Telegram Bot for Gemini API

This Telegram bot, developed using the Aiogram library, provides a convenient interface for interacting with the Google Gemini API. It allows users to harness the power of Gemini models directly within Telegram.

## Key Features:

*   **Gemini API Integration:** The bot utilizes the Google Gemini API to process text and image-based requests.
*   **Model Selection:** Users can choose between two experimental Gemini models:
    *   **Gemini 2.0 Flash:** A fast model ideal for tasks requiring quick and precise responses, such as working with recent news. It analyzes images and processes text information as if it were an entire library of books.
    *   **Gemini 2.0 Flash Thinking:** Offers deeper analysis, suitable for detailed responses and complex queries. It can delve into details like several books, drawing on knowledge gained during its training. It also analyzes images.
*   **Long Message Handling:** The bot intelligently handles long messages that Telegram may split into multiple parts. It waits up to 3 seconds to gather all parts of a message from a single user into one request.
*   **Image Analysis:** The bot is capable of processing multiple images sent by a user simultaneously and analyzes each of them, including any image captions.
*   **`/clear` Command:** Allows users to clear their request history (both text and image-based) and previously uploaded images, ensuring privacy and control.
*   **`/model` Command:** Enables users to switch between available Gemini models at any time.
*   **Text Formatting:** The bot supports text formatting using HTML markup (bold, italic, monospace, strikethrough, etc.).

## How the Bot Works:

The bot generates a prompt for Gemini, which includes the chat history, the current user query, and descriptions of all attached images. Based on this data, Gemini generates a response that is sent to the user. Due to Telegram's limitations, the bot attempts to split the response into multiple messages if it becomes too long.

## How to Run the Bot:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your_username/your_repository
    cd your_repository
    ```
    *Replace `https://github.com/your_username/your_repository` with the actual URL of your repository.*

2.  **Create a Virtual Environment (venv):**
    A virtual environment helps manage dependencies for your project in isolation. Here's how to create one for different operating systems:

    *   **Windows:**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
        *   The first command creates a virtual environment named `venv`.
        *   The second command activates the virtual environment.
    *   **macOS and Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
        *   The first command creates a virtual environment named `venv`.
        *   The second command activates the virtual environment.

    After activating the virtual environment, you'll see `(venv)` at the beginning of your terminal prompt, indicating that the virtual environment is active.

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Make sure you have the virtual environment activated.*

4.  **Configure Environment Variables:**
    You need to change variables in .env files to yours

5.  **Run the Bot:**
    ```bash
    python main.py
