# ---------- 2. NEXT CREATE: backend/repository.py ----------
from typing import List, Optional, Generic, TypeVar, Type, cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.selectable import Select
from sqlmodel import Session, select

from .models import User, Todo
from .schemas import UserCreate, UserUpdate, TodoCreate, TodoUpdate
from .security import get_password_hash

# Generic type variables
T = TypeVar('T')
U = TypeVar('U')


class BaseRepository(Generic[T, U]):
    """Generic base repository for CRUD operations."""

    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def get(self, id: int) -> Optional[T]:
        """Get an item by ID."""
        return self.session.get(self.model_class, id)

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get multiple items with pagination."""
        query = cast(Select, select(self.model_class).offset(skip).limit(limit))
        result = self.session.exec(query).all()
        return cast(List[T], result)

    def _create(self, create_schema: U) -> T:
        """Base create method to be extended by child classes."""
        raise NotImplementedError("Subclasses must implement create method")

    def _update(self, db_obj: T, update_schema: U) -> T:
        """Base update method to be extended by child classes."""
        raise NotImplementedError("Subclasses must implement update method")

    def delete(self, id: int) -> Optional[T]:
        """Delete an item by ID."""
        db_obj = self.get(id)
        if db_obj:
            self.session.delete(db_obj)
            self.session.commit()
        return db_obj


class UserRepository(BaseRepository[User, UserCreate]):
    """Repository for User entity."""

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        query = cast(Select, select(User).where(User.email == email))
        return self.session.exec(query).first()

    def create(self, user_create: UserCreate) -> User:
        """Create a new user."""
        try:
            hashed_password = get_password_hash(user_create.password)
            user_data = user_create.model_dump(exclude={"password"})

            db_user = User(
                **user_data,
                hashed_password=hashed_password
            )

            self.session.add(db_user)
            self.session.commit()
            self.session.refresh(db_user)
            return db_user
        except IntegrityError as e:
            self.session.rollback()
            if "UNIQUE constraint failed: user.email" in str(e):
                raise ValueError(f"User with email {user_create.email} already exists")
            raise ValueError(f"Error creating user: {str(e)}")
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating user: {str(e)}")

    def update(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update a user."""
        db_user = self.get(user_id)
        if not db_user:
            return None

        try:
            update_data = user_update.model_dump(exclude_unset=True)

            # Handle password update separately
            if "password" in update_data:
                hashed_password = get_password_hash(update_data.pop("password"))
                db_user.hashed_password = hashed_password

            # Update other fields
            for key, value in update_data.items():
                setattr(db_user, key, value)

            self.session.add(db_user)
            self.session.commit()
            self.session.refresh(db_user)
            return db_user
        except IntegrityError as e:
            self.session.rollback()
            if "UNIQUE constraint failed: user.email" in str(e):
                raise ValueError(f"User with this email already exists")
            raise ValueError(f"Error updating user: {str(e)}")
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error updating user: {str(e)}")


class TodoRepository(BaseRepository[Todo, TodoCreate]):
    """Repository for Todo entity."""

    def __init__(self, session: Session):
        super().__init__(session, Todo)

    def get_by_owner(self, owner_id: int, skip: int = 0, limit: int = 100) -> List[Todo]:
        """Get todos by owner ID."""
        query = cast(Select, select(Todo)
                     .where(Todo.owner_id == owner_id)
                     .offset(skip)
                     .limit(limit))
        result = self.session.exec(query).all()
        return cast(List[Todo], result)

    def get_user_todo(self, todo_id: int, owner_id: int) -> Optional[Todo]:
        """Get a specific todo owned by a user."""
        query = cast(Select, select(Todo)
                     .where(Todo.id == todo_id, Todo.owner_id == owner_id))
        return self.session.exec(query).first()

    def create(self, todo_create: TodoCreate, owner_id: int) -> Todo:
        """Create a new todo for a user."""
        try:
            todo_data = todo_create.model_dump()
            db_todo = Todo(**todo_data, owner_id=owner_id)

            self.session.add(db_todo)
            self.session.commit()
            self.session.refresh(db_todo)
            return db_todo
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating todo: {str(e)}")

    def update(self, todo_id: int, todo_update: TodoUpdate, owner_id: int) -> Optional[Todo]:
        """Update a todo owned by a user."""
        db_todo = self.get_user_todo(todo_id, owner_id)
        if not db_todo:
            return None

        try:
            update_data = todo_update.model_dump(exclude_unset=True)

            for key, value in update_data.items():
                setattr(db_todo, key, value)

            self.session.add(db_todo)
            self.session.commit()
            self.session.refresh(db_todo)
            return db_todo
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error updating todo: {str(e)}")

    def delete_user_todo(self, todo_id: int, owner_id: int) -> Optional[Todo]:
        """Delete a todo owned by a user."""
        db_todo = self.get_user_todo(todo_id, owner_id)
        if db_todo:
            try:
                self.session.delete(db_todo)
                self.session.commit()
                return db_todo
            except Exception as e:
                self.session.rollback()
                raise ValueError(f"Error deleting todo: {str(e)}")
        return None
