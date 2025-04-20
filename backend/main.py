
from datetime import timedelta
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from . import crud, models, security
from .database import get_session, init_db

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/token", response_model=security.Token)
async def login_for_access_token(session: Session = Depends(get_session), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user_by_email(session=session, email=form_data.username) # Use email as username
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users/", response_model=models.UserRead)
def create_user(user: models.UserCreate, session: Session = Depends(get_session)):
    db_user = crud.get_user_by_email(session=session, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    created_user = crud.create_user(session=session, user=user)
    # Convert User to UserRead before returning
    return models.UserRead(id=created_user.id, email=created_user.email, is_active=created_user.is_active)


@app.get("/users/me/", response_model=models.UserRead)
async def read_users_me(current_user: models.User = Depends(security.get_current_active_user)):
    # Convert User to UserRead before returning
    return models.UserRead(id=current_user.id, email=current_user.email, is_active=current_user.is_active)


@app.get("/users/me/todos/", response_model=List[models.TodoRead])
def read_own_todos(
    session: Session = Depends(get_session),
    current_user: models.User = Depends(security.get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    todos = crud.get_todos(session=session, owner_id=current_user.id, skip=skip, limit=limit)
    # Convert List[Todo] to List[TodoRead]
    return [models.TodoRead.from_orm(todo) for todo in todos]


@app.post("/users/{user_id}/todos/", response_model=models.TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo_for_user(
    todo: models.TodoCreate,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(security.get_current_active_user)
):
    # User can only create todos for themselves in this setup
    if not current_user:
         raise HTTPException(status_code=403, detail="Operation not permitted")
    created_todo = crud.create_user_todo(session=session, todo=todo, user_id=current_user.id)
    # Convert Todo to TodoRead before returning
    return models.TodoRead.from_orm(created_todo)

@app.get("/todos/", response_model=List[models.TodoRead])
def read_todos(
    session: Session = Depends(get_session),
    current_user: models.User = Depends(security.get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    # This endpoint might be redundant if /users/me/todos/ is preferred
    # Or adjust to allow admins to see all todos, etc.
    todos = crud.get_todos(session=session, owner_id=current_user.id, skip=skip, limit=limit)
    return [models.TodoRead.from_orm(todo) for todo in todos]

@app.get("/todos/{todo_id}", response_model=models.TodoReadWithOwner) # Example using TodoReadWithOwner
def read_todo(
    todo_id: int,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(security.get_current_active_user)
):
    db_todo = crud.get_todo(session=session, todo_id=todo_id, owner_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    # Eagerly load the owner relationship or handle it as needed
    # This assumes the owner is loaded or accessible via db_todo.owner
    owner_read = models.UserRead.from_orm(current_user) # Assuming current_user is the owner
    return models.TodoReadWithOwner(**models.TodoRead.from_orm(db_todo).dict(), owner=owner_read)


@app.put("/todos/{todo_id}", response_model=models.TodoRead)
def update_todo_item(
    todo_id: int,
    todo_in: models.TodoUpdate,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(security.get_current_active_user)
):
    db_todo = crud.get_todo(session=session, todo_id=todo_id, owner_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    updated_todo = crud.update_todo(session=session, db_todo=db_todo, todo_in=todo_in)
    return models.TodoRead.from_orm(updated_todo)


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo_item(
    todo_id: int,
    session: Session = Depends(get_session),
    current_user: models.User = Depends(security.get_current_active_user)
):
    db_todo = crud.get_todo(session=session, todo_id=todo_id, owner_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    crud.delete_todo(session=session, db_todo=db_todo)
    return None # Return None for 204 response

# Add __init__.py files to make 'backend' a package
