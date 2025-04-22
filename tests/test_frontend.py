import unittest
from unittest.mock import patch, MagicMock
import pytest
import os
import json
import flet as ft
import requests

# Import the main function from main.py
from frontend.main import main

class MockResponse:
    """Mock response object for API calls"""
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data) if json_data else ""

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            response = MagicMock()
            response.status_code = self.status_code
            response.json = lambda: self.json_data
            response.text = self.text
            raise requests.HTTPError("Mock HTTP Error", response=response)


class TestFrontendLogin(unittest.TestCase):
    """Test suite for frontend login functionality"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create a mock page object
        self.page = MagicMock(spec=ft.Page)
        self.page.route = ""
        self.page.views = []

        # Initialize app with mock page
        main(self.page)

        # Extract important components from the view by simulating route change
        self.page.route = "/login"
        route_change_handler = self.page.on_route_change
        route_change_handler(self.page.route)

        # Get references to input fields and error text
        login_view = self.page.views[0]
        login_content = login_view.controls[0]

        # Email and password fields should be at index 1 and 2
        # (after the title text at index 0)
        self.email_input = login_content.controls[1]
        self.password_input = login_content.controls[2]
        self.error_text = login_content.controls[3]

        # Find login button
        self.login_button = login_content.controls[4]

        # Reset mock call history for page.go after setup
        self.page.go.reset_mock()

    @patch('requests.post')
    def test_successful_login(self, mock_post):
        """Test successful login flow"""
        # Mock responses for API calls
        token_response = MockResponse({"access_token": "test_token", "token_type": "bearer"}, 200)
        mock_post.return_value = token_response

        # Set input values
        self.email_input.value = "test@example.com"
        self.password_input.value = "password123"

        # Trigger login
        with patch('requests.get', return_value=MockResponse({"id": 1, "email": "test@example.com", "is_active": True}, 200)):
            self.login_button.on_click(None)

        # Verify navigation to todos page
        self.page.go.assert_called_with("/todos")

        # Verify snackbar was shown with success message
        assert self.page.snack_bar is not None
        assert self.page.snack_bar.bgcolor == ft.colors.GREEN

        # Check that input fields were cleared
        assert self.email_input.value == ""
        assert self.password_input.value == ""

    def test_empty_fields_validation(self):
        """Test validation for empty fields"""
        # Set empty values
        self.email_input.value = ""
        self.password_input.value = ""

        # Trigger login
        self.login_button.on_click(None)

        # Verify error message
        assert self.error_text.value == "Email and password are required."

        # No navigation should happen to /todos
        assert not any(call.args[0] == "/todos" for call in self.page.go.call_args_list)

    def test_empty_email_validation(self):
        """Test validation for empty email field"""
        # Set empty email but valid password
        self.email_input.value = ""
        self.password_input.value = "password123"

        # Trigger login
        self.login_button.on_click(None)

        # Verify error message
        assert self.error_text.value == "Email and password are required."

        # No navigation should happen to /todos
        assert not any(call.args[0] == "/todos" for call in self.page.go.call_args_list)

    def test_empty_password_validation(self):
        """Test validation for empty password field"""
        # Set valid email but empty password
        self.email_input.value = "test@example.com"
        self.password_input.value = ""

        # Trigger login
        self.login_button.on_click(None)

        # Verify error message
        assert self.error_text.value == "Email and password are required."

        # No navigation should happen to /todos
        assert not any(call.args[0] == "/todos" for call in self.page.go.call_args_list)

    @patch('requests.post')
    def test_invalid_credentials(self, mock_post):
        """Test login with invalid credentials"""
        # Mock unauthorized response
        mock_post.return_value = MockResponse(
            {"detail": "Incorrect email or password"},
            401
        )

        # Set input values
        self.email_input.value = "test@example.com"
        self.password_input.value = "wrongpassword"

        # Trigger login
        self.login_button.on_click(None)

        # Verify error message contains "Incorrect email or password"
        assert "Incorrect email or password" in self.error_text.value

        # No navigation should happen to /todos
        assert not any(call.args[0] == "/todos" for call in self.page.go.call_args_list)

    @patch('requests.post')
    def test_server_error(self, mock_post):
        """Test handling of server error during login"""
        # Mock server error response
        mock_post.return_value = MockResponse(
            {"detail": "Internal server error"},
            500
        )

        # Set input values
        self.email_input.value = "test@example.com"
        self.password_input.value = "password123"

        # Trigger login
        self.login_button.on_click(None)

        # Verify error message contains status code
        assert "500" in self.error_text.value

        # No navigation should happen to /todos
        assert not any(call.args[0] == "/todos" for call in self.page.go.call_args_list)

    @patch('requests.post')
    def test_connection_error(self, mock_post):
        """Test handling of connection error during login"""
        # Mock connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Set input values
        self.email_input.value = "test@example.com"
        self.password_input.value = "password123"

        # Trigger login
        self.login_button.on_click(None)

        # Verify error message contains "Connection"
        assert "Connection" in self.error_text.value

        # No navigation should happen to /todos
        assert not any(call.args[0] == "/todos" for call in self.page.go.call_args_list)
