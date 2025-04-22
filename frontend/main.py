import flet as ft
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def main(page: ft.Page):
    page.title = "Todo App"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT

    # State variables
    auth_token = None
    current_user = None

    # --- API Client ---
    def api_call(method, endpoint, data=None, headers=None):
        nonlocal auth_token
        url = f"{BACKEND_URL}{endpoint}"
        _headers = {"Content-Type": "application/json"}

        # Add authorization header if token exists
        if auth_token:
            _headers["Authorization"] = f"Bearer {auth_token}"

        # Update headers with any additional ones provided
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

            response.raise_for_status()

            # Return None for No Content responses
            if response.status_code == 204:
                return None

            return response.json()
        except requests.exceptions.RequestException as e:
            error_detail = e.response.json().get('detail', str(e)) if hasattr(e, 'response') and e.response else str(e)
            print(f"API Error: {error_detail}")
            show_snackbar(f"API Error: {error_detail}", ft.colors.RED)
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
    error_text = ft.Text(color=ft.colors.RED)

    def show_snackbar(message, color):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # --- User Management ---
    def login(e):
        nonlocal auth_token, current_user
        error_text.value = ""

        email = email_input.value
        password = password_input.value

        if not email or not password:
            error_text.value = "Email and password are required."
            page.update()
            return

        try:
            # FastAPI's OAuth2 token endpoint expects form data
            response = requests.post(
                f"{BACKEND_URL}/token",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
            auth_token = token_data.get("access_token")

            if auth_token:
                # Get current user info
                user_info = api_call("GET", "/users/me/")
                if user_info:
                    current_user = user_info
                    # Clear inputs and navigate to todo view
                    email_input.value = ""
                    password_input.value = ""
                    page.go("/todos")
                    show_snackbar("Login successful!", ft.colors.GREEN)
                else:
                    auth_token = None
                    error_text.value = "Failed to get user information."
            else:
                error_text.value = "Login failed: No token received."
        except requests.exceptions.HTTPError as http_err:
            detail = "Login failed"
            try:
                error_json = http_err.response.json()
                detail = error_json.get("detail", detail)
            except ValueError:
                pass
            error_text.value = f"{detail} (Status: {http_err.response.status_code})"
            print(f"HTTP error during login: {http_err} - {http_err.response.text}")
        except requests.exceptions.RequestException as req_err:
            error_text.value = f"Connection error: {req_err}"
            print(f"Request error during login: {req_err}")
        except Exception as ex:
            error_text.value = f"An unexpected error occurred: {ex}"
            print(f"Unexpected error during login: {ex}")

        page.update()

    def signup(e):
        error_text.value = ""

        email = email_input.value
        password = password_input.value

        if not email or not password:
            error_text.value = "Email and password are required."
            page.update()
            return

        if len(password) < 8:
            error_text.value = "Password must be at least 8 characters long."
            page.update()
            return

        # Backend expects UserCreate model (email, password, is_active)
        user_data = {"email": email, "password": password}
        response = api_call("POST", "/users/", data=user_data)

        if response and "id" in response:
            show_snackbar("Signup successful! Please log in.", ft.colors.GREEN)
            email_input.value = ""
            password_input.value = ""
            error_text.value = ""
            page.go("/login")
        else:
            error_text.value = "Signup failed. Email might already exist."

        page.update()

    def logout(e):
        nonlocal auth_token, current_user
        auth_token = None
        current_user = None
        show_snackbar("Logged out.", ft.colors.BLUE)
        page.go("/login")

    # --- Todo Management ---
    def add_todo(e):
        title = todo_input.value

        if not title:
            show_snackbar("Todo title cannot be empty.", ft.colors.ORANGE)
            return

        # Create todo with title and optional description
        todo_data = {"title": title, "description": ""}
        response = api_call("POST", "/todos/", data=todo_data)

        if response and "id" in response:
            todo_input.value = ""
            load_todos()
            show_snackbar("Todo added!", ft.colors.GREEN)
        else:
            show_snackbar("Failed to add todo.", ft.colors.RED)

        page.update()

    def delete_todo(todo_id):
        response = api_call("DELETE", f"/todos/{todo_id}")

        # DELETE returns 204 No Content on success
        if response is None:
            load_todos()
            show_snackbar("Todo deleted.", ft.colors.GREEN)
        else:
            show_snackbar("Failed to delete todo.", ft.colors.RED)

        page.update()

    def toggle_todo_done(todo_id, current_status):
        update_data = {"is_done": not current_status}
        response = api_call("PUT", f"/todos/{todo_id}", data=update_data)

        if response and "id" in response:
            load_todos()
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
            page.go("/login")
            return

        # Get todos for current user
        todos = api_call("GET", "/users/me/todos/")
        todos_list_view.controls.clear()

        if todos is not None:
            if isinstance(todos, list):
                if todos:
                    for todo in todos:
                        todos_list_view.controls.append(create_todo_item_row(todo))
                else:
                    todos_list_view.controls.append(ft.Text("No todos yet!"))
            else:
                todos_list_view.controls.append(ft.Text("Could not load todos."))
                print(f"Unexpected API response format for todos: {todos}")
        else:
            todos_list_view.controls.append(ft.Text("Could not load todos."))

        page.update()

    # --- Views ---
    login_view_content = ft.Column(
        [
            ft.Text("Login", size=30, weight=ft.FontWeight.BOLD),
            email_input,
            password_input,
            error_text,
            ft.ElevatedButton("Login", on_click=login, width=300),
            ft.TextButton("Don't have an account? Sign Up", on_click=lambda e: page.go("/signup")),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )

    signup_view_content = ft.Column(
        [
            ft.Text("Sign Up", size=30, weight=ft.FontWeight.BOLD),
            email_input,
            password_input,
            error_text,
            ft.ElevatedButton("Sign Up", on_click=signup, width=300),
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
                    ft.Text("My Todos", size=30, weight=ft.FontWeight.BOLD),
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
            ft.Container(content=todos_list_view, expand=True),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )

    # --- Routing ---
    def route_change(route):
        page.views.clear()

        if page.route == "/login":
            email_input.value = ""
            password_input.value = ""
            error_text.value = ""
            page.views.append(
                ft.View(
                    "/login",
                    [login_view_content],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    vertical_alignment=ft.MainAxisAlignment.CENTER
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
            if not auth_token:
                page.go("/login")
                return

            load_todos()
            page.views.append(
                ft.View(
                    "/todos",
                    [todos_view_content],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    vertical_alignment=ft.MainAxisAlignment.START
                )
            )
        else:
            # Default route handling
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

    # Start at the login page
    page.go("/login")


# Run the app
if __name__ == "__main__":
    ft.app(target=main)
