
import flet as ft
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def main(page: ft.Page):
    page.title = "Todo App"
    page.vertical_alignment = ft.MainAxisAlignment.START # Center content vertically
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER # Center content horizontally
    page.theme_mode = ft.ThemeMode.LIGHT # Start with light theme

    auth_token = None # Store the JWT token

    # --- API Client ---
    def api_call(method, endpoint, data=None, headers=None):
        nonlocal auth_token
        url = f"{BACKEND_URL}{endpoint}"
        _headers = {"Content-Type": "application/json"}
        if auth_token:
            _headers["Authorization"] = f"Bearer {auth_token}"
        if headers:
            _headers.update(headers)

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=_headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=_headers, json=data)
            elif method.upper() == "PUT":
                 response = requests.put(url, headers=_headers, json=data)
            elif method.upper() == "DELETE":
                 response = requests.delete(url, headers=_headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            if response.status_code == 204: # No Content
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            show_snackbar(f"API Error: {e.response.json().get('detail', e) if e.response else e}", ft.colors.RED)
            return None
        except Exception as e:
             print(f"An unexpected error occurred: {e}")
             show_snackbar(f"Error: {e}", ft.colors.RED)
             return None


    # --- UI Components & Views ---
    email_input = ft.TextField(label="Email", autofocus=True, width=300)
    password_input = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
    todo_input = ft.TextField(label="New Todo", width=300)
    todos_list_view = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
    error_text = ft.Text(color=ft.colors.RED) # To display login/signup errors

    def show_snackbar(message, color):
        page.show_snack_bar(
            ft.SnackBar(ft.Text(message), bgcolor=color)
        )

    # --- Event Handlers ---
    def login(e):
        nonlocal auth_token
        error_text.value = "" # Clear previous errors
        email = email_input.value
        password = password_input.value
        if not email or not password:
            error_text.value = "Email and password are required."
            page.update()
            return

        # Use application/x-www-form-urlencoded for token endpoint
        try:
            response = requests.post(
                f"{BACKEND_URL}/token",
                data={"username": email, "password": password}, # FastAPI's OAuth2PasswordRequestForm expects form data
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
            auth_token = token_data.get("access_token")
            if auth_token:
                # Clear inputs and navigate to todo view
                email_input.value = ""
                password_input.value = ""
                email_input.focus() # Reset focus
                page.go("/todos")
                show_snackbar("Login successful!", ft.colors.GREEN)
            else:
                 error_text.value = "Login failed: No token received."

        except requests.exceptions.HTTPError as http_err:
             detail = "Login failed"
             try:
                 # Try to get specific error from backend response
                 error_json = http_err.response.json()
                 detail = error_json.get("detail", detail)
             except ValueError: # If response is not JSON
                 pass
             error_text.value = f"{detail} (Status: {http_err.response.status_code})"
             print(f"HTTP error during login: {http_err} - {http_err.response.text}") # Log detailed error
        except requests.exceptions.RequestException as req_err:
            error_text.value = f"Connection error: {req_err}"
            print(f"Request error during login: {req_err}") # Log detailed error
        except Exception as ex:
             error_text.value = f"An unexpected error occurred: {ex}"
             print(f"Unexpected error during login: {ex}") # Log detailed error

        page.update()


    def signup(e):
        error_text.value = "" # Clear previous errors
        email = email_input.value
        password = password_input.value
        if not email or not password:
             error_text.value = "Email and password are required."
             page.update()
             return

        # Note: Backend expects UserCreate model (email, password, is_active)
        # is_active defaults to True in the model
        user_data = {"email": email, "password": password}
        response = api_call("POST", "/users/", data=user_data)

        if response and "id" in response:
            show_snackbar("Signup successful! Please log in.", ft.colors.GREEN)
            email_input.value = ""
            password_input.value = ""
            error_text.value = "" # Clear error on success
            page.go("/login") # Redirect to login view after signup
        else:
            # Error handled by api_call's snackbar
            # If api_call returns None, an error occurred
             if not page.snack_bar: # Avoid overwriting API error snackbar if already shown
                 error_text.value = "Signup failed. Email might already exist." # Generic fallback

        page.update()

    def add_todo(e):
        title = todo_input.value
        if not title:
            show_snackbar("Todo title cannot be empty.", ft.colors.ORANGE)
            page.update()
            return

        todo_data = {"title": title, "description": ""} # Add description later if needed
        # The backend endpoint is /users/{user_id}/todos/, but we rely on auth
        # The /todos/ POST endpoint should implicitly use the authenticated user
        # Let's adjust backend or frontend call if needed. Assuming /todos/ POST works with auth:
        response = api_call("POST", "/todos/", data=todo_data) # Assuming POST /todos/ is the correct user-specific endpoint

        if response and "id" in response:
            todo_input.value = ""
            load_todos() # Reload the list
            show_snackbar("Todo added!", ft.colors.GREEN)
        else:
             show_snackbar("Failed to add todo.", ft.colors.RED)
        page.update()


    def delete_todo(todo_id):
        response = api_call("DELETE", f"/todos/{todo_id}")
        # DELETE returns 204 No Content on success, api_call returns None for 204
        if response is None: # Check for successful deletion (None means 204 was likely returned)
             load_todos()
             show_snackbar("Todo deleted.", ft.colors.GREEN)
        else:
             # Error handled by api_call's snackbar
             show_snackbar("Failed to delete todo.", ft.colors.RED) # Fallback message
        page.update()

    def toggle_todo_done(todo_id, current_status):
        update_data = {"is_done": not current_status}
        response = api_call("PUT", f"/todos/{todo_id}", data=update_data)
        if response and "id" in response:
             load_todos() # Reload to show updated status
             show_snackbar("Todo status updated.", ft.colors.GREEN)
        else:
            show_snackbar("Failed to update todo status.", ft.colors.RED)
        page.update()

    def create_todo_item_row(todo):
        return ft.Row(
            [
                ft.Checkbox(
                    value=todo['is_done'],
                    label=todo['title'],
                    on_change=lambda e, tid=todo['id'], status=todo['is_done']: toggle_todo_done(tid, status),
                ),
                ft.IconButton(
                    ft.icons.DELETE_OUTLINE,
                    tooltip="Delete Todo",
                    on_click=lambda e, tid=todo['id']: delete_todo(tid),
                    icon_color=ft.colors.RED_ACCENT_700
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def load_todos():
        nonlocal auth_token
        if not auth_token:
            page.go("/login") # Redirect if not logged in
            return

        # Backend endpoint for user's todos: /users/me/todos/
        todos = api_call("GET", "/users/me/todos/")

        todos_list_view.controls.clear() # Clear existing todos
        if todos is not None: # Check if API call was successful
            if isinstance(todos, list):
                if todos:
                    for todo in todos:
                        todos_list_view.controls.append(create_todo_item_row(todo))
                else:
                     todos_list_view.controls.append(ft.Text("No todos yet!"))
            else:
                # Handle cases where API returns unexpected data format
                 todos_list_view.controls.append(ft.Text("Could not load todos."))
                 print(f"Unexpected API response format for todos: {todos}")

        else:
            # Error handled by api_call's snackbar
            todos_list_view.controls.append(ft.Text("Could not load todos."))
            # Optionally force logout if token seems invalid (e.g., 401 error)
            # Check specific error in api_call if needed
            # if error seems to be 401:
            #    auth_token = None
            #    page.go("/login")

        page.update()


    def logout(e):
        nonlocal auth_token
        auth_token = None
        show_snackbar("Logged out.", ft.colors.BLUE)
        page.go("/login")


    # --- Views ---
    login_view_content = ft.Column(
        [
            ft.Text("Login", size=30),
            email_input,
            password_input,
            error_text,
            ft.ElevatedButton("Login", on_click=login),
            ft.TextButton("Don't have an account? Sign Up", on_click=lambda e: page.go("/signup")),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )

    signup_view_content = ft.Column(
        [
            ft.Text("Sign Up", size=30),
            email_input,
            password_input,
            error_text,
            ft.ElevatedButton("Sign Up", on_click=signup),
            ft.TextButton("Already have an account? Login", on_click=lambda e: page.go("/login")),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )

    todos_view_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("My Todos", size=30),
                    ft.IconButton(ft.icons.LOGOUT, tooltip="Logout", on_click=logout)
                 ],
                 alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),

            ft.Row(
                [
                    todo_input,
                    ft.FloatingActionButton(icon=ft.icons.ADD, on_click=add_todo),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Divider(),
            ft.Container(content=todos_list_view, expand=True), # Make list view expandable
        ],
        # alignment=ft.MainAxisAlignment.START, # Align content to the top
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True # Make the main column take available space
    )


    # --- Routing ---
    def route_change(route):
        page.views.clear()
        if page.route == "/login":
            email_input.value = "" # Clear fields when navigating
            password_input.value = ""
            error_text.value = ""
            page.views.append(
                ft.View(
                    "/login",
                    [login_view_content],
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      vertical_alignment=ft.MainAxisAlignment.CENTER # Center view content
                )
            )
        elif page.route == "/signup":
             email_input.value = ""
             password_input.value = ""
             error_text.value = ""
             page.views.append(
                ft.View(
                    "/signup",
                    [signup_view_content],
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      vertical_alignment=ft.MainAxisAlignment.CENTER
                )
            )
        elif page.route == "/todos":
            if not auth_token: # Protect route
                 page.go("/login")
                 return # Stop processing this route change

            load_todos() # Load todos when navigating to the view
            page.views.append(
                ft.View(
                    "/todos",
                    [todos_view_content],
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      vertical_alignment=ft.MainAxisAlignment.START # Align todo view content to top
                )
            )
        else:
             # Default route if logged in, else login
             if auth_token:
                 page.go("/todos")
             else:
                 page.go("/login")


        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Start at the login page or todos page if already logged in (implement token storage later)
    page.go("/login")


# Run the app
ft.app(target=main) # Use target=main for desktop app

# To run as a web app, you might use:
# ft.app(target=main, view=ft.AppView.WEB_BROWSER)

