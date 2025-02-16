# SAFEPLANT CREDENTIALS
#--------------------------------
# This file is the log in page of the application 

# Imports
#----------------
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, 
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
import sys
import os
import json
# from SafePlant_main import SafePlant_Function
from extra_safeplant import SafePlant_Function
import webbrowser


# Creating the Welcome Window
#---------------------------
class WelcomeWindow(QWidget):

    # setting the attributes in the class
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username  # username is supplied by the user
        self.setWindowTitle("Welcome to SafePlant!")
        self.setGeometry(400, 300, 450, 350)
        self.setFixedSize(600, 500)

        # Adjusting the Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Setting the Welcome message
        welcome_label = QLabel("Welcome to SafePlant+!")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(welcome_label)

        # Main message when a user successfully creates a new account
        message = (
            "We're excited to have you join our community. "
            "SafePlant+ empowers botanists with user-friendly tools to diagnose and manage plant diseases.\n\n"
            "Explore the app and discover how it can help you protect plant health.\n\n"
            "Need help? Our support team is here for you.\n\n"
            "Thank you for choosing SafePlant+!"
        )
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(message_label)

        # Allowing the user to download the user manual
        self.download_label = QLabel()
        self.download_label.setText("<a href='#'>📥 Download User Manual</a>")
        self.download_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_label.setStyleSheet("color: #3498db; font-size: 12pt;")
        self.download_label.setOpenExternalLinks(False)
        self.download_label.linkActivated.connect(self.download_manual)
        layout.addWidget(self.download_label)

        # Proceed button
        proceed_button = QPushButton("Get Started")
        proceed_button.setStyleSheet(
            "background-color: #4CAF50; color: white; font-size: 14px; padding: 10px; border-radius: 5px;"
        )
        proceed_button.clicked.connect(self.proceed)
        layout.addWidget(proceed_button)

        self.setLayout(layout)

    # Close the welcome window and open the main functionality page
    def proceed(self):
        self.main_functionality = SafePlant_Function(self.username)
        self.main_functionality.show()
        self.close()

    # Opens the User Manual Download Link
    def download_manual(self):
        # manual_url = "https://docs.google.com/document/d/1epcijPu7IArWrepSad3ebw0D3E27BAFh/export?format=pdf"
        manual_url = "https://docs.google.com/document/d/1CxbGwalFjfDs8Y8PV6rL6l1k-sQPRQBf/export?format=pdf"
        webbrowser.open(manual_url)

# Separate Window for signing up
#--------------------------------
class SignUpWindow(QWidget):
    # Creating the attributes
    def __init__(self, user_credentials, user_data_storage, parent=None):
        super().__init__(parent)
        self.user_credentials = user_credentials  # reference to the same data dict
        self.user_data_storage = user_data_storage

        # Set 
        self.setWindowTitle("Create Your SafePlant+ Account")
        self.setGeometry(450, 300, 400, 350)
        self.setFixedSize(500, 400)

        # Adjusting the Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        header_label = QLabel("Create Your SafePlant+ Account")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header_label)

        # Username
        self.signup_username = QLineEdit()
        self.signup_username.setPlaceholderText("Username")
        self.signup_username.setFixedHeight(35)
        layout.addWidget(self.signup_username)

        # Password
        self.signup_password = QLineEdit()
        self.signup_password.setPlaceholderText("Password")
        self.signup_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.signup_password.setFixedHeight(35)
        layout.addWidget(self.signup_password)

        # Sign Up Button
        self.signup_button = QPushButton("Sign Up")
        self.signup_button.clicked.connect(self.handle_signup)
        layout.addWidget(self.signup_button)

        # Link to go back to Login
        back_label = QLabel()
        back_label.setText("<a href='#'>Already have an account? Log In here</a>")
        back_label.setOpenExternalLinks(False)  # we want to handle click ourselves
        back_label.linkActivated.connect(self.back_to_login)
        back_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        back_label.setStyleSheet("color: #3498db; font-size: 11pt;")
        layout.addWidget(back_label)

        # Footer
        spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        layout.addSpacerItem(spacer)

        footer_label = QLabel("Developed by: Satini Sai Keerthan, Lee Xiu Wen, Leong Jun Ming & Tiah Wei Xuan")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer_label)

        self.setLayout(layout)

    # Function to handle signup related erros
    def handle_signup(self):
        # Setting up the attributes
        user_username = self.signup_username.text().strip()
        user_password = self.signup_password.text().strip()

        # Return error message if all fields are not filled or if username already exists 
        if not user_username or not user_password:
            QMessageBox.warning(self, "ERROR:", "Please fill in all fields!")
            return

        if user_username in self.user_credentials:
            QMessageBox.warning(self, "ERROR:", "Username Already Exists! Please try again!")
            return

        # Create a new user
        self.user_credentials[user_username] = {
            "password": user_password,
            "is_new": True
        }
        self.save_user_data()

        # Confirmation of account creation
        QMessageBox.information(self, "Success!", "Account has been created! Welcome To SafePlant+")

        # Show the welcome window immediately
        self.welcome_window = WelcomeWindow(user_username)
        self.welcome_window.show()

        # Close this SignUpWindow (so user won't see sign-up again)
        self.close()

    # Close sign-up window and show the login window again
    def back_to_login(self):
        self.login_window = SafePlant_Welcome()
        self.login_window.show()
        self.close()

    def save_user_data(self):
        try:
            with open(self.user_data_storage, "w") as f:
                json.dump(self.user_credentials, f)
        except:
            QMessageBox.critical(self, "Error", "There has been a problem saving User Data!")

# Main class window consisting of all the LogIn, SignUp Forget Password and Welcome Window 
class SafePlant_Welcome(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login to SafePlant+")
        self.setGeometry(400, 300, 400, 450)
        self.setFixedSize(500, 400)

        self.user_data_storage = os.path.join(os.path.dirname(__file__), "user_file.json")
        self.load_user_data()

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        self.nav_label = QLabel("Login to SafePlant+")
        self.nav_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nav_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(self.nav_label)

        # Username input
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        self.login_username.setFixedHeight(35)
        main_layout.addWidget(self.login_username)

        # Password input
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setFixedHeight(35)
        main_layout.addWidget(self.login_password)

        # Log In button
        self.login_button = QPushButton("Log In")
        self.login_button.clicked.connect(self.LogIn)
        main_layout.addWidget(self.login_button)

        # Forgot Password button
        self.reset_password_button = QPushButton("Forgot Password?")
        self.reset_password_button.clicked.connect(self.forget_password)
        self.reset_password_button.setStyleSheet("font-size: 10pt; color: #666;") 
        main_layout.addWidget(self.reset_password_button)

        # Sign Up link
        signup_label = QLabel()
        signup_label.setText("<a href='#'>New to SafePlant+? Sign Up here</a>")
        signup_label.setOpenExternalLinks(False)  
        signup_label.linkActivated.connect(self.open_sign_up)  # method below
        signup_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signup_label.setStyleSheet("color: #3498db; font-size: 11pt; margin-top: 8px;")
        main_layout.addWidget(signup_label)

        # Footer
        spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addSpacerItem(spacer)

        footer_label = QLabel("Developed by: Satini Sai Keerthan, Lee Xiu Wen, Leong Jun Ming & Tiah Wei Xuan")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("font-size: 10pt; color: #999;")
        main_layout.addWidget(footer_label)

        self.setLayout(main_layout)

    def load_user_data(self):
       # Load credentials file in JSON format
        if not os.path.exists(self.user_data_storage):
            with open(self.user_data_storage, 'w') as f:
                json.dump({}, f)

        try:
            with open(self.user_data_storage, 'r') as f:
                self.user_credentials = json.load(f)

            # Migrate old structure if needed
            for username, value in self.user_credentials.items():
                if isinstance(value, str):  # old style just storing password
                    self.user_credentials[username] = {
                        "password": value,
                        "is_new": False
                    }
            self.save_user_data()
        except (json.JSONDecodeError, IOError):
            QMessageBox.critical(self, "Error", "There has been a problem loading User Data!")
            self.user_credentials = {}

    def save_user_data(self):
        try:
            with open(self.user_data_storage, "w") as f:
                json.dump(self.user_credentials, f)
        except:
            QMessageBox.critical(self, "Error", "There has been a problem saving User Data!")

    def LogIn(self):

        user_username = self.login_username.text().strip()
        user_password = self.login_password.text().strip()
 
        # check credentials
        if (
            user_username in self.user_credentials and
            self.user_credentials[user_username]["password"] == user_password
        ):
            QMessageBox.information(self, "Log In Successful!", "Welcome to SafePlant+!")
            self.hide()
            try:
                self.SafePlant = SafePlant_Function(user_username)
                self.SafePlant.show()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open SafePlant_Function: {str(e)}")
                self.show()
        else:
            QMessageBox.warning(self, "Login Failed!", "Please check your credentials again or reset your password.")

    def forget_password(self):
        # same logic as before
        username, ok = QInputDialog.getText(self, "Reset Password", "Enter your Username!")
        if username and ok:
            if username in self.user_credentials:
                password_new, ok = QInputDialog.getText(self, "New Password", "Enter your new password!")
                if password_new and ok:
                    # store in the dictionary
                    self.user_credentials[username]["password"] = password_new
                    self.save_user_data()
                    QMessageBox.information(self, "Success!", "Your password has been updated!")
                else:
                    QMessageBox.warning(self, "ERROR!", "Please input valid Password!")
            else:
                QMessageBox.warning(self, "ERROR!", "Username does not exist! Please Try again!")
        else:
            QMessageBox.warning(self, "ERROR!", "Please input valid Username!")

    def open_sign_up(self):
        """
        Opens the separate sign-up window and passes references
        to the shared user data dictionary and file.
        """
        self.signup_window = SignUpWindow(self.user_credentials, self.user_data_storage)
        self.signup_window.show()

#Running Application with custom stylesheet using CSS.
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget {
            background-color: #f7f7f7;
            color: #333;
            font-family: 'Verdana';
            font-size: 11pt;
        }
        QLabel#Header-Label {
            font-size: 22px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        }
        QLineEdit {
            background-color: #fff;
            border: 1px solid #aaa;
            border-radius: 5px;
            padding: 8px;
            font-size: 10pt;
        }
        QPushButton {
            background-color: #5cb85c;
            color: white;
            border-radius: 5px;
            padding: 8px 15px;
        }
        QPushButton:hover {
            background-color: #4cae4c;
        }
        QPushButton:pressed {
            background-color: #398439;
        }
    """)
    window = SafePlant_Welcome()
    window.show()
    sys.exit(app.exec())
