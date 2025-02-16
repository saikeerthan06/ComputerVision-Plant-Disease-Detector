import logging
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QHBoxLayout, QMessageBox, QTextEdit, QScrollArea, QLineEdit, QListWidget,
    QListWidgetItem, QProgressBar, QInputDialog, QGridLayout, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QMouseEvent, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QSize
import threading
import os
import shutil
import datetime
import sys
import appdirs  
# import google.generativeai as genai
import uuid
import json
import spacy
import tensorflow as tf
# from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.applications.mobilenet_v3 import preprocess_input
# from google import genai
import openai
# from openai import OpenAI
import cv2
import numpy as np
from PyQt6.QtCore import QTimer


#OpenAI Key for integrating ChatGPT into application. 
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY


# Directory where application stores data 
def get_app_directory():
    app_name = "PlantDiseaseDetector"
    app_author = "SafePlant" 
    data_dir = appdirs.user_data_dir(app_name, app_author)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

app_directory = get_app_directory()


# Logging for debugging purposes
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(app_directory, "app_debug.log")),
        logging.StreamHandler()
    ]
)

# Get the history of chats interacted between user and GPT
def get_chat_history_dir():
    chat_dir = os.path.join(app_directory, 'chatgpt_chats')
    os.makedirs(chat_dir, exist_ok=True)
    return chat_dir


def last_used(dt):
    now = datetime.datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minutes ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hours ago"
    else:
        days = int(seconds / 86400)
        return f"{days} days ago"
    



class ClickableFrame(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

#Following Class is to display the different interactions the user did to ChatGPT 
# -------------------------------------------------------------------------------
class ChatListItem(QWidget):
    def __init__(self, chat, rename_callback):
        super().__init__()
        self.chat = chat
        self.rename_callback = rename_callback  # Callback function for renaming the chat
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self.chat_name_label = QLabel(chat['chat_name'])
        self.chat_name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.chat_name_label)

        # Time since last message
        if chat['messages']:
            last_interacted_str = chat['messages'][-1]['timestamp']
            last_interacted_time = datetime.datetime.strptime(last_interacted_str, "%Y-%m-%d %H:%M:%S")
            time_label_text = last_used(last_interacted_time)
        else:
            time_label_text = "Never used"

        # Instantiate the time label beside the GPT chat name
        self.time_label = QLabel(time_label_text)
        self.time_label.setFont(QFont("Arial", 10))
        self.time_label.setStyleSheet("color: gray;")
        layout.addWidget(self.time_label)

        #Aligning buttons to the right 
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addItem(spacer)

        self.continue_button = QPushButton("Continue")
        self.continue_button.setFixedSize(QSize(80, 30))
        self.continue_button.setObjectName("ContinueButton")
        layout.addWidget(self.continue_button)

        # Rename Chat Button
        self.rename_button = QPushButton("Rename")
        self.rename_button.setFixedSize(QSize(80, 30))
        self.rename_button.setObjectName("RenameButton")
        self.rename_button.clicked.connect(self.rename_chat)
        layout.addWidget(self.rename_button)

        # Delete Chat Button
        self.delete_button = QPushButton("Delete")
        self.delete_button.setFixedSize(QSize(80, 30))
        self.delete_button.setObjectName("DeleteButton")
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def rename_chat(self):
        """Invoke the rename callback when the Rename button is clicked."""
        self.rename_callback(self.chat)

# Creating GPT History Window - to display GPT History and Chat
#----------------------------------------------------------------
class GPTHistoryWindow(QWidget):
    # Signal to notify when the window is closed
    closed = pyqtSignal()  

    def __init__(self, parent=None, model=None):
        super().__init__(parent)
        self.model = model  # Reference to the openai module
        self.setWindowTitle("ChatGPT Chat History")
        self.setGeometry(600, 300, 600, 500)
        self.setFixedSize(600, 500)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setObjectName("ChatHistoryWindow")
        
        self.chat_history_dir = get_chat_history_dir()
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)
        
        # Header
        header = QLabel("Your ChatGPT Chat History")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        main_layout.addWidget(header)
        
        # Scroll Area for chat list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.chat_list_layout = QVBoxLayout(scroll_content)
        self.chat_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Populate the chat list
        self.populate_chat_list()
        
        # New Chat Button
        self.new_chat_button = QPushButton("Start New Chat")
        self.new_chat_button.setFixedHeight(40)
        self.new_chat_button.clicked.connect(self.start_new_chat)
        main_layout.addWidget(self.new_chat_button)
        
    def populate_chat_list(self):
        # Clear existing items
        for i in reversed(range(self.chat_list_layout.count())):
            widget = self.chat_list_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        chats = self.get_all_chats()
        if not chats:
            no_chat_label = QLabel("No chat history available.")
            no_chat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_chat_label.setFont(QFont("Arial", 12))
            self.chat_list_layout.addWidget(no_chat_label)
            return

        for chat in chats:
            chat_item = ChatListItem(chat, rename_callback=self.rename_chat)
            chat_item.continue_button.clicked.connect(lambda checked, c=chat: self.continue_chat(c))
            chat_item.delete_button.clicked.connect(lambda checked, c=chat: self.delete_chat(c))
            self.chat_list_layout.addWidget(chat_item)
            logging.debug(f"Added chat entry: {chat['chat_name']}")

    def rename_chat(self, chat):
        # Prompt the user to rename a chat and update its name.
        new_name, ok = QInputDialog.getText(self, "Rename Chat", "Enter new name for the chat:", text=chat['chat_name'])
        if ok and new_name.strip():
            new_name = new_name.strip()
            chat['chat_name'] = new_name
            chat_file = os.path.join(self.chat_history_dir, f"{chat['chat_id']}.json")
            try:
                with open(chat_file, 'w') as f:
                    json.dump(chat, f, indent=4)
                QMessageBox.information(self, "Success", f"Chat renamed to '{new_name}'.")
                logging.info(f"Renamed chat to: {new_name}")
                self.populate_chat_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename chat: {str(e)}")
                logging.error(f"Failed to rename chat: {e}")
        else:
            logging.info("Chat rename cancelled.")

    def get_all_chats(self):
        chats = []
        for filename in os.listdir(self.chat_history_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.chat_history_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        chat = json.load(f)
                        chats.append(chat)
                except (json.JSONDecodeError, IOError):
                    logging.warning(f"Failed to load chat file: {filepath}")
                    continue
        chats.sort(key=lambda x: x['messages'][-1]['timestamp'] if x['messages'] else x.get('created_at', ''), reverse=True)
        return chats
    

    # Function allows user to get back into the GPT chat and interact with the bot 
    def continue_chat(self, chat):
        """Open the chat window for the selected chat."""
        try:
            self.chat_window = GPTChatWindow(chat, model=self.model)
            self.chat_window.show()
            logging.info(f"Continuing chat: {chat['chat_name']}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to continue chat: {str(e)}")
            logging.error(f"Error continuing chat '{chat['chat_name']}': {e}")
        
    def delete_chat(self, chat):
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the chat '{chat['chat_name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            chat_file = os.path.join(self.chat_history_dir, f"{chat['chat_id']}.json")
            try:
                os.remove(chat_file) # Deletes everything associated with the chat
                QMessageBox.information(self, "Deleted", f"Chat '{chat['chat_name']}' has been deleted.")
                logging.info(f"Deleted chat: {chat['chat_name']}")
                self.populate_chat_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete chat: {str(e)}")
                logging.error(f"Error deleting chat '{chat['chat_name']}': {e}")
    
    def start_new_chat(self):
        chat_id = str(uuid.uuid4())
        chat_name = f"Chat {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        new_chat = { # define the naming structure of the chat 
            "chat_id": chat_id,
            "chat_name": chat_name,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": []
        }
        chat_file = os.path.join(self.chat_history_dir, f"{chat_id}.json") # create new chatfile using os
        try:
            with open(chat_file, 'w') as f:
                json.dump(new_chat, f, indent=4)
            logging.info(f"Started new chat: {chat_name}")
            self.open_chat_window(new_chat)
            self.populate_chat_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start a new chat: {str(e)}")
            logging.error(f"Error starting new chat '{chat_name}': {e}")
    
    def open_chat_window(self, chat):
        self.chat_window = GPTChatWindow(chat, self, self.model)
        self.chat_window.show()
        logging.info(f"ChatWindow shown for chat: {chat['chat_name']}")
    
    def closeEvent(self, event):
        self.closed.emit()
        event.accept()
        logging.info("ChatHistoryWindow closed.")

# This class handles the styling and functionalities related to the Chat Window
class GPTChatWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, chat, parent=None, model=None):
        super().__init__(parent)
        self.nlp = spacy.load("en_core_web_sm") # Use Spacy's Package in order to format GPT's responses, making it more readable as compared to just putting text out there. 
        self.chat = chat  # Chat dictionary loaded from history
        self.model = model  # Reference to the openai module (for ChatCompletion)
        self.chat_history_dir = get_chat_history_dir()
        
        # Define dimentions of the chat window
        self.setWindowTitle(f"ChatGPT Chat - {self.chat['chat_name']}")
        self.setGeometry(650, 350, 600, 600)
        self.setFixedSize(600, 600)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setObjectName("ChatWindow")
        
        # Main layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        self.setLayout(self.layout)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setObjectName("ChatDisplay")
        self.chat_display.setFont(QFont("Arial", 11))
        self.chat_display.setStyleSheet("""
            QTextEdit#ChatDisplay {
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.layout.addWidget(self.chat_display)
        
        # Populate existing messages
        self.load_messages()
        
        # User input area
        input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your message here...")
        self.user_input.setObjectName("UserInput")
        self.user_input.setFont(QFont("Arial", 11))
        self.user_input.setStyleSheet("""
            QLineEdit#UserInput {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 8px;
                font-size: 11pt;
            }
        """)
        input_layout.addWidget(self.user_input)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("SendButton")
        self.send_button.setFixedSize(QSize(80, 40))
        self.send_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.send_button.setStyleSheet("""
            QPushButton#SendButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-size: 11pt;
            }
            QPushButton#SendButton:hover {
                background-color: #45a049;
            }
            QPushButton#SendButton:pressed {
                background-color: #398439;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        self.layout.addLayout(input_layout)
        
        # Optional: Pressing Enter sends the message
        self.user_input.returnPressed.connect(self.send_message)


    # Use Spacy NLP package to format 
    def format_chatgpt_response(self, response_text, timestamp):
        doc = self.nlp(response_text)
        # Start with the "ChatGPT" header
        formatted_response = (
            f'<p style="color: green; font-weight: bold;">'
            f'ChatGPT [{timestamp}]:</p>'
        )

        for sent in doc.sents:
            sentence = sent.text.strip()

            # Example logic for headings
            if any(keyword in sentence.lower()
                for keyword in ["symptoms", "transmission", "structure", "overview"]):
                formatted_response += f'<h3 style="color: green; margin-top: 10px;">{sentence}</h3>'

            # Example logic for bullet points
            elif sentence.startswith("-") or sentence.startswith("*"):
                formatted_response += f'<ul><li>{sentence[1:].strip()}</li></ul>'

            else:
                # Normal paragraph
                formatted_response += f'<p style="margin-bottom: 5px;">{sentence}</p>'

        return formatted_response
    
    # Load messges from the history and display using SpaCy formatting
    def load_messages(self):
        try:
            for message in self.chat['messages']:
                sender = message['sender']
                text = message['message']
                timestamp = message['timestamp']

                if sender == "User":
                    # Simple formatting for User messages
                    formatted_message = (
                        f'<p style="color: blue; font-weight: bold;">You [{timestamp}]:</p>'
                        f'<p style="color: black;">{text}</p>'
                    )
                else:
                    # Use your new spaCy-based formatting for GPT
                    formatted_message = self.format_chatgpt_response(text, timestamp)

                self.chat_display.append(formatted_message)

            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )
            logging.info("Chat messages loaded successfully.")

        except Exception as e:
            logging.error(f"Error loading chat messages: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load chat messages: {str(e)}")

    
    # Use GPT4o Model to generate responses to user inputs
    def generate_chatgpt_response(self, user_text):

        try:
            response = self.model.ChatCompletion.create(
                model="gpt-4o", #GPT model selection
                messages=[
                    {"role": "system", "content": "You are a helpful assistant, housed in a PyQT6 Application where your primary goal is to help users of the application with any plant disease queries they may have."}, # custom instructions to model, so that it caters more towards plant care. 
                    {"role": "user", "content": user_text}
                ]
            )
            if response and response.choices:
                return response.choices[0].message.content.strip()
            else:
                return ""
        except Exception as e:
            logging.error(f"Error generating ChatGPT response: {e}")
            return ""

    # send message to chatgpt function 
    def send_message(self):
        try:
            user_text = self.user_input.text().strip()
            if not user_text:
                QMessageBox.warning(self, "Empty Message", "Please enter a message to send.")
                return

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_user_message = f'<p style="color: blue; font-weight: bold;">You [{timestamp}]:</p><p style="color: black;">{user_text}</p>'
            self.chat_display.append(formatted_user_message)
            self.chat['messages'].append({
                "sender": "User",
                "message": user_text,
                "timestamp": timestamp
            }) #shows the user message's timestamp. 
            self.save_chat_history()
            self.user_input.clear()

            # Generate ChatGPT response
            bot_response = self.generate_chatgpt_response(user_text)
            if bot_response:
                # Use the spaCy-based formatting
                formatted_response = self.format_chatgpt_response(bot_response, timestamp)
                self.chat_display.append(formatted_response)

                # Save to your JSON chat data
                self.chat['messages'].append({
                    "sender": "ChatGPT",
                    "message": bot_response,
                    "timestamp": timestamp
                })
                self.save_chat_history()
            else:
                formatted_response = '<p style="color: green; font-weight: bold;">ChatGPT:</p><p style="color: black;">I\'m not sure how to respond to that.</p>'
                self.chat_display.append(formatted_response)

            self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
        except Exception as e:
            logging.error(f"Error in send_message: {e}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
    
    def save_chat_history(self):
        chat_file = os.path.join(self.chat_history_dir, f"{self.chat['chat_id']}.json")
        try:
            with open(chat_file, 'w') as f:
                json.dump(self.chat, f, indent=4)
            logging.info(f"Saved chat history for chat ID: {self.chat['chat_id']}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save chat history: {str(e)}")
            logging.error(f"Failed to save chat history for chat ID {self.chat['chat_id']}: {e}")
    
    def closeEvent(self, event):
        self.closed.emit()
        event.accept()
        logging.info("ChatWindow closed.")


# This class is used to display the history of the user's scans, with image thumbnail, editable name field and editable description fields with three buttons "Save", "Delete" & "View Results"
class IndividualHistoryWindow(QWidget):

    def __init__(self, history_folder, user_username):
        super().__init__()
        self.history_folder = history_folder # save into folder
        self.user_username = user_username
        self.setWindowTitle(f"{self.user_username}'s Individual History - SafePlant+")
        self.setGeometry(350, 250, 900, 600)
        self.setFixedSize(1000, 700)
        #self.model = model  # Now correctly received from the caller
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setObjectName("IndividualHistoryWindow")
    
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(self.scroll_widget)
    
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)
    
        main_layout.addWidget(scroll_area)
    
        # Instantiate the delete all buttons which deletes every scan from the history window 
        self.delete_all_scans_button = QPushButton("Delete All Individual Scans")
        self.delete_all_scans_button.setObjectName("DeleteAllIndividualScansButton")
        self.delete_all_scans_button.setFixedHeight(40)
        self.delete_all_scans_button.clicked.connect(self.delete_all_scans)
        main_layout.addWidget(self.delete_all_scans_button)
    
        self.setLayout(main_layout)
        self.load_history()
    
    def load_history(self):
        # Clear previous items
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        header = QLabel("Individual Scans:")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.scroll_layout.addWidget(header)
        # Show only image files (ignore directories/groups)
        image_files = [file for file in os.listdir(self.history_folder) 
                       if os.path.isfile(os.path.join(self.history_folder, file)) 
                       and file.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            no_scan_label = QLabel("No individual scans available.")
            no_scan_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_scan_label.setFont(QFont("Arial", 12))
            self.scroll_layout.addWidget(no_scan_label)
            return
        for file in image_files:
            file_path = os.path.join(self.history_folder, file)
            self.scroll_layout.addWidget(self.create_scan_box(file, file_path))
            logging.debug(f"Added individual scan box for: {file_path}")

    
    # Creates a field with image thumbnail, editable name and description text fields.  
    def create_scan_box(self, name, file_path):
        box = QHBoxLayout()
        box.setSpacing(10)

        # Image Thumbnail
        img_label = QLabel()
        pixmap = QPixmap(file_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)
        img_label.setPixmap(pixmap)
        img_label.setFixedSize(100, 100)
        box.addWidget(img_label)

        # Editable image name
        name_edit = QLineEdit(os.path.splitext(name)[0])
        name_edit.setFixedWidth(200)
        box.addWidget(name_edit)

        # Editable description
        desc_edit = QTextEdit()
        desc_edit.setFixedWidth(300)
        desc_file = f"{file_path}.txt"
        if os.path.exists(desc_file):
            with open(desc_file, 'r') as f:
                desc_edit.setPlainText(f.read())
        else:
            desc_edit.setPlaceholderText("Enter description here...")
        box.addWidget(desc_edit)

        # Instantiate and design Save Button
        save_button = QPushButton("Save")
        save_button.setFixedSize(QSize(80, 30))
        save_button.setObjectName("SaveButton")
        save_button.clicked.connect(lambda _, ip=file_path, ne=name_edit, de=desc_edit: self.save_changes(ip, ne, de))
        box.addWidget(save_button)

        # Instantiate and design Delete Button
        delete_button = QPushButton("Delete")
        delete_button.setFixedSize(QSize(80, 30))
        delete_button.setObjectName("DeleteButton")
        delete_button.clicked.connect(lambda _, ip=file_path: self.delete_image(ip))
        box.addWidget(delete_button)

        # Instantiate and design View Results Button
        view_button = QPushButton("View Results")
        view_button.setFixedSize(QSize(100, 30))
        view_button.setObjectName("ViewResultsButton")
        view_button.clicked.connect(lambda _, ip=file_path: self.open_results_window(ip))
        box.addWidget(view_button)

        wrapper = QWidget()
        wrapper.setLayout(box)
        return wrapper
    
    # save all the changes to a file. 
    def save_changes(self, image_path, name_edit, desc_edit):
        try:
            new_name = name_edit.text().strip()
            ext = os.path.splitext(image_path)[1]
            if not new_name.lower().endswith(ext):
                new_name += ext
            new_path = os.path.join(os.path.dirname(image_path), new_name)
            if os.path.exists(new_path) and new_path != image_path:
                QMessageBox.warning(self, "Error", "Image with this name exists!")
                logging.warning(f"Duplicate file name attempted: {new_path}")
                return
            os.rename(image_path, new_path)
            with open(f"{new_path}.txt", 'w') as f:
                f.write(desc_edit.toPlainText())
            QMessageBox.information(self, "Saved", "Changes have been saved!")
            logging.info(f"Changes saved for image: {new_path}")
            self.load_history()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")
            logging.error(f"Failed to save changes for image {image_path}: {e}")

    def open_results_window(self, image_path):
        self.results_window = ResultsWindow(image_path=image_path, parent=None)
        self.results_window.show()
       

    # function to delete the image from the view history by removing the image path stored using os     
    def delete_image(self, image_path):
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
            txt_path = f"{image_path}.txt"
            if os.path.exists(txt_path):
                os.remove(txt_path)
            QMessageBox.information(self, "Deleted", "Image deleted!")
            logging.info(f"Deleted image: {image_path}")
            self.load_history()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete image: {str(e)}")
            logging.error(f"Failed to delete image {image_path}: {e}")
    
    # Deletes all scans from the view history by removing the entire history folder stored using os
    def delete_all_scans(self):
        confirmation = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete all individual scans?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
    
        if confirmation == QMessageBox.StandardButton.Yes:
            try:
                for file in os.listdir(self.history_folder):
                    file_path = os.path.join(self.history_folder, file)
                    if os.path.isfile(file_path) and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        os.remove(file_path)
                    desc_file = f"{file_path}.txt"
                    if os.path.exists(desc_file):
                        os.remove(desc_file)
                QMessageBox.information(self, "Success", "All individual scans have been deleted.")
                logging.info("All individual scans deleted by user.")
                self.load_history()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete individual scans: {str(e)}")
                logging.error(f"Failed to delete individual scans: {e}")


#Main app functionality, displaying the drag and drop scan box, the list below, clear all, clear selected, view history, quick scam buttons. 
class SafePlant_Function(QWidget):

    def __init__(self, user_username="test_user"):
        super().__init__()
        self.user_username = user_username
        self.setWindowTitle(f"Welcome {self.user_username} - SafePlant+")
        self.setGeometry(300, 200, 800, 600)
        self.setObjectName("Function-Window")
        self.individual_history_window = None

        # Set up ChatGPT integration by using the openai module
        self.chatgpt = openai #instantiate openai

        try:
            CWD = os.getcwd() # getting the current working directory
            model_path = os.path.join(CWD, 'florav13.keras') # works with any device as it is using the cwd
            print(f"MODEL PATH:{model_path}")
            self.flora = tf.keras.models.load_model(model_path)
           
            logging.info("MobileNetV2 model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load MobileNetV2 model: {e}")
            QMessageBox.critical(self, "Model Load Error", f"Failed to load MobileNetV2 model:\n{str(e)}")
            self.flora = None

        self.function_layout = QVBoxLayout() #use vertical box layout for the main screen
        self.function_layout.setContentsMargins(20, 20, 20, 20)
        self.function_layout.setSpacing(15)

        # create a header section to house the view history button and the chatgpt button, with the quick scan button below. 
        header_section = QHBoxLayout()
        header_section.setSpacing(10)

        self.history_button = QPushButton("View History")
        self.history_button.setObjectName("History-Button")
        self.history_button.clicked.connect(self.view_history) # connects to the function
        self.history_button.setFixedHeight(40)
        header_section.addWidget(self.history_button)

        self.chatgpt_button = QPushButton("ChatGPT Chatbot") 
        self.chatgpt_button.setObjectName("ChatGPT-Button")
        self.chatgpt_button.clicked.connect(self.open_chat_history) #connects to open chatgpt button
        self.chatgpt_button.setFixedHeight(40) 
        header_section.addWidget(self.chatgpt_button)

        self.function_layout.addLayout(header_section)
        self.function_layout.addLayout(header_section)

        # self.group_name_label = QLabel("You are currently using: None")
        # self.group_name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        # self.group_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.function_layout.addWidget(self.group_name_label)

        # instantiates the quick scan button, setting up the CSS class name and connecting it to a function 
        self.quick_scan_button = QPushButton("Quick Scan")
        self.quick_scan_button.setObjectName("Process-Button")
        self.quick_scan_button.clicked.connect(self.process_images) 
        self.quick_scan_button.setFixedHeight(40)
        self.function_layout.addWidget(self.quick_scan_button)

        # enables drag and drop functionality 
        self.setAcceptDrops(True)
        self.dropped_items = []
        self.setup_drag_drop_ui()


        self.history_folder = os.path.join(app_directory, 'history', self.user_username)
        os.makedirs(self.history_folder, exist_ok=True)
        self.current_group = None
        self.individual_history_window = None
        self.chat_history_window = None

        self.setLayout(self.function_layout)

    # opens the chatgpt chat history
    def open_chat_history(self):
        """Open the ChatGPT Chat History window as a standalone."""
        try:
            if not self.chatgpt:
                QMessageBox.critical(self, "Error", "ChatGPT integration is not configured properly.")
                logging.error("ChatGPT is not configured. Cannot open Chat History.")
                return
            self.chat_history_window = GPTHistoryWindow(model=self.chatgpt)
            self.chat_history_window.show()
            logging.info("ChatHistoryWindow opened successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Chat History: {str(e)}")
            logging.error(f"Failed to open Chat History: {e}")


    
    # enables drag and drop functionalities through PyQT6 
    def setup_drag_drop_ui(self):
        """Sets up the drag-and-drop area and list view."""
        drag_drop_text = QLabel("Drag & Drop Images or click the box to select images!")
        drag_drop_text.setObjectName("DragDropText")
        drag_drop_text.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        drag_drop_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.function_layout.addWidget(drag_drop_text)
    
        self.drag_box = ClickableFrame()
        self.drag_box.setFixedHeight(150)
        self.drag_box.setObjectName("DragDropBox")
        self.drag_box.clicked.connect(self.select_images)
        self.drag_box.setStyleSheet("""
            QFrame#DragDropBox {
                border: 2px dashed #aaa;
                background-color: #ffffff;
            }
        """)
    
        # Sets up, and define drag and drop functionality 
        drag_drop_layout = QVBoxLayout(self.drag_box)
        drag_drop_layout.setContentsMargins(0, 0, 0, 0)
        drag_drop_layout.setSpacing(0)
    
        # Add a label inside the drag box
        drag_box_label = QLabel("Drop your images here or click to browse.")
        drag_box_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drag_box_label.setFont(QFont("Arial", 11))
        drag_drop_layout.addWidget(drag_box_label)
    
        self.function_layout.addWidget(self.drag_box)
    
        self.dropped_item_list = QListWidget()
        self.dropped_item_list.setObjectName("DroppedItemList")
        self.dropped_item_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.dropped_item_list.setFont(QFont("Arial", 10))
        self.function_layout.addWidget(self.dropped_item_list)
    
        # Buttons to clear dropped items
        list_button_layout = QHBoxLayout()
        self.clear_list_button = QPushButton("Clear All")
        self.clear_list_button.setObjectName("ClearListButton")
        self.clear_list_button.clicked.connect(self.clear_list)
        self.clear_list_button.setFixedHeight(35)
        list_button_layout.addWidget(self.clear_list_button)
    
        # Clear selected buttons to delete certain droppd images. 
        self.clear_selected_button = QPushButton("Clear Selected")
        self.clear_selected_button.setObjectName("ClearSelectedButton")
        self.clear_selected_button.clicked.connect(self.clear_selected)
        self.clear_selected_button.setFixedHeight(35)
        list_button_layout.addWidget(self.clear_selected_button)
    
        self.function_layout.addLayout(list_button_layout)
    
    # users can select images from their file explorer/finder. 
    def select_images(self):
       
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_paths, _ = file_dialog.getOpenFileNames(
            self, "Select Images", "", "Images (*.png *.jpg *.jpeg)" # Accepts .png .jpg and .jpeg file extensions 
        )
        added_images = 0 # counter increases when images are dropped
        for path in file_paths:
            if path not in self.dropped_items:
                self.dropped_items.append(path)
                self.dropped_item_list.addItem(path)
                added_images += 1
        if added_images > 0:
            QMessageBox.information(self, "Images Uploaded!", f"{added_images} image(s) added!") # when counter increases. 
            logging.info(f"Added {added_images} image(s) via file dialog.")
    
    # remove any items in the list through clear function
    def clear_list(self):
        self.dropped_items.clear()
        self.dropped_item_list.clear()
        QMessageBox.information(self, "Cleared!", "All dropped items have been cleared!")
        logging.info("Cleared all dropped images.")
    
    # Use selectedItems function to remove any items selected in the list. 
    def clear_selected(self):
        selected_images = self.dropped_item_list.selectedItems()
        if not selected_images:
            QMessageBox.information(self, "No Images Selected", "Please select one or more images to remove.")
            logging.warning("No images selected to remove.")
            return
        counter = 0
        for item in selected_images:
            file_path = item.text()
            if file_path in self.dropped_items:
                self.dropped_items.remove(file_path)
            self.dropped_item_list.takeItem(self.dropped_item_list.row(item))
            counter += 1
        QMessageBox.information(self, "Cleared!", f"Cleared {counter} item(s) from the list!")
        logging.info(f"Cleared {counter} selected image(s).")
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # Check if at least one of the dragged files is an image
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg')):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    # Functions to handle any dropped files
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            new_images = 0 # counter for new images
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg')): 
                    if file_path not in self.dropped_items:
                        self.dropped_items.append(file_path)
                        self.dropped_item_list.addItem(file_path)
                        logging.info(f"Image dragged into app: {file_path}")
                        new_images += 1
            if new_images > 0:
                QMessageBox.information(self, "Images Dropped!", f"{new_images} image(s) added via drag-and-drop.")
                logging.info(f"Added {new_images} image(s) via drag-and-drop.")
            else:
                QMessageBox.information(
                    self, "No New Images",
                    "No new images were added. They might already be in the list."
                )
                logging.info("No new images added via drag-and-drop.")
   
    
    def process_images(self):
        try:
            if not self.dropped_items:
                QMessageBox.warning(self, "Error!", "There are no files to process!")
                logging.warning("Process images attempted with no files.")
                return
            target_folder = self.current_group if self.current_group else self.history_folder
            total_images = len(self.dropped_items)
            progress = QProgressBar()
            progress.setObjectName("QuickScanProgressBar")
            progress.setMaximum(total_images)
            progress.setValue(0)
            self.function_layout.addWidget(progress)
            logging.info(f"Processing {total_images} image(s).")
    
            for i, image_path in enumerate(self.dropped_items, start=1):
                file_name = os.path.basename(image_path)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                new_file_name = f"{timestamp}_{file_name}"
                destination_path = os.path.join(target_folder, new_file_name)
                shutil.copy(image_path, destination_path)
                logging.info(f"Copied {image_path} to {destination_path}")
                # Create a corresponding description file
                with open(f"{destination_path}.txt", 'w') as f:
                    f.write("Enter description here...")
                logging.debug(f"Created description file for {destination_path}")
                # Update progress
                progress.setValue(i)
    
            # Remove the progress bar after completion
            self.function_layout.removeWidget(progress)
            progress.deleteLater()
    
            QMessageBox.information(self, "Processed", "Images processed! Check your history.")
            logging.info("Image processing completed.")
    
            # Clear dragged images after processing
            self.dropped_items.clear()
            self.dropped_item_list.clear()
    
            if self.individual_history_window:
                self.individual_history_window.load_history()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process images: {str(e)}")
            logging.error(f"Failed to process images: {e}")
    
    # opens individual scan history in the application
    def view_history(self):
       
        try:
            # If we have not created an IndividualHistoryWindow yet, create one
            if self.individual_history_window is None:
                self.individual_history_window = IndividualHistoryWindow(
                    self.history_folder,
                    self.user_username
                )
            # Show (or re-show) the same window
            self.individual_history_window.show()
            logging.info("Opened individual scan history window.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open history: {str(e)}")
            logging.error(f"Failed to open history: {e}")


    # opens GPT chatbot, forgot to change name when we were using Gemini. 
    def open_gemini_history(self):
        try:
            # Ensure model is initialized before proceeding
            if not self.gemini:
                QMessageBox.critical(self, "Error", "Gemini model is not configured properly.")
                logging.error("Gemini model is not configured. Cannot open Gemini Chat History.")
                return

            # Create and show the Gemini Chat History window
            self.gemini_history_window = GPTHistoryWindow(model=self.gemini)
            self.gemini_history_window.show()
            logging.info("GeminiHistoryWindow opened successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Gemini Chat History: {str(e)}")
            logging.error(f"Failed to open Gemini Chat History: {e}")
    
    def on_history_closed(self):
        self.gemini_history_window = None  # Remove the reference when history window is closed
        logging.info("GeminiHistoryWindow closed.")


# Class to handle the standalone Results Window when the user clicks on the "View Results" button
class ResultsWindow(QWidget):
    gpt_response_received = pyqtSignal(dict)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.image_path = image_path
        # (Model loading and other initialization code here …)
    
        CWD = os.getcwd() # getting the current working directory
        model_path = os.path.join(CWD, 'florav13.keras')
        self.flora = tf.keras.models.load_model(model_path)
        self.setWindowTitle("Scan Results - SafePlant+")
        self.setGeometry(700, 350, 600, 500)
        self.setFixedSize(600, 500)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setObjectName("ResultsWindow")
        # Set up your layout, image display, etc.
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(12)
        self.setLayout(self.layout)

        # (Add header, image display, inference results, etc.)
        header_label = QLabel("Model Inference Results")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.layout.addWidget(header_label)

        self.image_label = QLabel()
        pixmap = QPixmap(self.image_path).scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)

        # Run inference
        self.predicted_label, self.confidence = self.run_inference(self.image_path)
        self.results_label = QLabel()
        self.results_label.setText(
            f"<b>Predicted Label:</b> {self.predicted_label}<br>"
            f"<b>Confidence Score:</b> {self.confidence:.1f}%<br>"
        )
        self.results_label.setFont(QFont("Arial", 12))
        self.layout.addWidget(self.results_label)

        # Buttons at the bottom
        button_layout = QHBoxLayout()

        self.return_button = QPushButton("Return to History")
        self.return_button.setFixedSize(130, 40)
        self.return_button.clicked.connect(self.return_to_history)
        button_layout.addWidget(self.return_button)

        self.ask_gpt_button = QPushButton("Ask GPT")
        self.ask_gpt_button.setFixedSize(130, 40)
        self.ask_gpt_button.clicked.connect(self.ask_gpt)
        button_layout.addWidget(self.ask_gpt_button)

        self.layout.addLayout(button_layout)

        # Connect the custom signal to the slot that opens the GPT chat window
        self.gpt_response_received.connect(self.open_gpt_window)

        # self.progress_bar = QProgressBar(self)
        # self.progress_bar.setRange(0, 0)  # Indeterminate mode
        # self.layout.addWidget(self.progress_bar)

    # Image preprocessing done before the model processes the image. Includes resizing, changing color from BGR to RGB so that MobileNetV3 can read it as OpenCV interpretates images as BGR. 
    def model_preprocess(self, image_path):
   
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Error: Could not load image from {image_path}")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
        img = cv2.resize(img, (224, 224))          # Resize to 224x224, suitable dimennsions for MobileNetV3
        img = preprocess_input(img.astype(np.float32))  # Ensure dtype is float32
        img = np.expand_dims(img, axis=0)          # Add batch dimension
        return img

    def run_inference(self, image_path):
        try:
            img = self.model_preprocess(image_path)  # Already has batch dimension
            preds = self.flora.predict(img)  # Directly use the processed img

            # Calculate the confidence score of the model to display it. 
            confidence = float(np.max(preds)) * 100
            class_idx = int(np.argmax(preds.flatten()))

            # List of classes that Flora can identify 
            label_list = ['Cherry_(including_sour)___healthy',
                          'Corn_(maize)___Northern_Leaf_Blight', 
                          'Corn_(maize)___healthy',
                          'Grape___Black_rot',
                          'Grape___Esca_(Black_Measles)',
                          'Peach___Bacterial_spot',
                          'Pepper,_bell___Bacterial_spot',
                          'Strawberry___healthy',
                          'Tomato___Early_blight',
                          'Tomato___Late_blight',
                          'Tomato___Leaf_Mold',
                          'Tomato___Target_Spot']
            predicted_label = label_list[class_idx] if class_idx < len(label_list) else "Unknown" # Unknown if the image does not represent any of the classes above. 
            return predicted_label, confidence

        except Exception as e:
            logging.error(f"Error running inference: {e}")
            return "Error", 0.0
        

    # Function to handle the "Return To History" Button, opening up the individual scan history
    def return_to_history(self):
        """Close this window to reveal the parent history window."""
        self.close()
        if self.parent_window is not None and hasattr(self.parent_window, "view_history"):
            self.parent_window.view_history() 

    # Function to handle the "ask gpt" button, allowing for an extra window with GPT's tailor made responses to a certain predicted label and confidence score. 
    def ask_gpt(self):
        info_gpt = QMessageBox()
        info_gpt.setIcon(QMessageBox.Icon.Information)
        info_gpt.setWindowTitle("Processing GPT Request")
        info_gpt.setText("Please wait while ChatGPT is processing your request. \n This may take some time!")

        info_gpt.setStandardButtons(QMessageBox.StandardButton.Ok)
    
        # Show the message box and wait for the user to acknowledge
        info_gpt.exec()

        
        threading.Thread(target=self.get_gpt_and_open_window, daemon=True).start()
        
    # Generates GPT response in the background, and then opens up the window with the finalised responses. 
    def get_gpt_and_open_window(self):
        try:
            initial_prompt = (
                f"Please provide additional insights on this scan result:\n"
                f"Predicted Label: {self.predicted_label}\n"
                f"Confidence: {self.confidence:.1f}%\n\n"
                "Include possible plant disease details, treatment suggestions, and further relevant context."
            )

            # Create a new chat object
            chat_id = str(uuid.uuid4())
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_chat = {
                "chat_id": chat_id,
                "chat_name": f"Scan GPT Chat {timestamp}",
                "created_at": timestamp,
                "messages": [
                    {"sender": "User", "message": initial_prompt, "timestamp": timestamp}
                ]
            }

            # Establish GPT to the certain type of predicted label 
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable assistant..."},
                    {"role": "user", "content": initial_prompt}
                ]
            )
            gpt_response = response.choices[0].message.content.strip()
            logging.info("GPT Response: %s", gpt_response)

            # Append GPT response to the chat
            new_chat["messages"].append({
                "sender": "ChatGPT",
                "message": gpt_response,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # Save the chat history as JSON
            chat_history_dir = get_chat_history_dir()  # your helper function
            chat_file = os.path.join(chat_history_dir, f"{chat_id}.json")
            with open(chat_file, 'w') as f:
                json.dump(new_chat, f, indent=4)

            # Emit the signal with the new chat data so the window opens on the main thread
            self.gpt_response_received.emit(new_chat)

        except Exception as e:
            logging.error("Error in get_gpt_and_open_window: %s", e)
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self, "GPT Error", f"Failed to open GPT chat: {str(e)}"
            ))

    # Open the GPT window with the tailored response to the particular label and the confidence score. 
    def open_gpt_window(self, chat_data):
        self.gpt_chat_window = GPTChatWindow(chat_data, model=openai)
        self.gpt_chat_window.show()
        self.gpt_chat_window.raise_()
        self.gpt_chat_window.activateWindow()


# Below is the main function to run the application, also including the CSS styling for the overall styling of the application. 
def main():
    app = QApplication(sys.argv)

    # Global StyleSheet
    app.setStyleSheet("""
    /* General application styling */
    QWidget#Function-Window, QWidget#GeminiHistoryWindow, QWidget#GeminiChatWindow, QWidget#Ask_History, QWidget#IndividualHistoryWindow, QWidget#GroupHistoryWindow, QWidget#GroupDetailsWindow {
        background-color: #f2f2f2;
        font-family: 'Arial';
        font-size: 11pt;
        color: #2c3e50;
    }

    /* Header Label Styling */
    QLabel#HeaderLabel, QLabel#SectionLabel {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 10px;
    }

    /* Drag & drop styling */
    QLabel#DragDropLabel, QLabel#DragDropText, QLabel#DragDropInstructions {
        font-weight: bold;
        font-size: 12px;
    }
    QFrame#DragDropBox, QFrame#ChatDisplay {
        border: 2px dashed #aaa;
        background-color: #ffffff;
    }
    QLabel#DragDropInstructions {
        font-style: italic;
        color: #666;
    }

    /* QListWidget Styling */
    QListWidget#ChatList, QListWidget#DroppedItemList, QListWidget#DraggedImagesList {
        border: 1px solid #ccc;
        background-color: #fff;
    }

    /* Buttons Styling */
    QPushButton#History-Button, QPushButton#New-Group-Button, QPushButton#Terminate-Group-Button, QPushButton#Gemini-Button, QPushButton#Process-Button, QPushButton#ContinueButton, QPushButton#DeleteButton, QPushButton#DeleteAllScansButton, QPushButton#DeleteAllIndividualScansButton, QPushButton#DeleteAllGroupScansButton, QPushButton#SendButton {
        background-color: #3498db;
        color: #ffffff;
        border-radius: 4px;
        padding: 6px 12px;
    }
    QPushButton#ContinueButton, QPushButton#DeleteButton, QPushButton#SaveButton, QPushButton#SendButton {
        background-color: #2ecc71;
    }
    QPushButton#DeleteButton {
        background-color: #e74c3c;
    }
    QPushButton#SendButton {
        background-color: #4CAF50;
    }
    QPushButton#ContinueButton:hover, QPushButton#DeleteButton:hover, QPushButton#SaveButton:hover, QPushButton#SendButton:hover {
        background-color: #2980b9;
    }
    QPushButton#ContinueButton:pressed, QPushButton#DeleteButton:pressed, QPushButton#SaveButton:pressed, QPushButton#SendButton:pressed {
        background-color: #1F4788;
    }
    QPushButton:disabled {
        background-color: #cccccc;
        color: #666666;
        border-radius: 4px;
        padding: 6px 12px;
    }

    /* ProgressBar Styling */
    QProgressBar#QuickScanProgressBar {
        border: 1px solid #ccc;
        height: 20px;
        border-radius: 4px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #3498db;
        width: 10px;
    }
    """)

    username = "test_user"  # Replace with actual username handling
    main_app = SafePlant_Function(username)
    main_app.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


