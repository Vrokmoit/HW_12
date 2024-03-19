from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from contactpr import schemas, models, database
from fastapi.security import OAuth2PasswordBearer
from auth import create_user, authenticate_user, create_jwt_token
from auth import get_current_user
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from .database import get_db

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.get("/")
async def read_root():
    return {"message": "Ласкаво просимо до мого додатку FastAPI!"}

# Маршрут для створення нового контакту
@router.post("/contacts/", response_model=schemas.Contact)
def create_contact(contact: schemas.ContactCreate, db: Session = Depends(get_db)):
    db_contact = models.Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

# Маршрут для отримання списку всіх контактів
@router.get("/contacts/", response_model=list[schemas.Contact])
def get_contacts_by_owner(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    contacts = db.query(models.Contact).filter(models.Contact.owner_id == current_user.id).all()
    return contacts

# Маршрут для отримання одного контакту по його ідентифікатору
@router.get("/contacts/{contact_id}", response_model=schemas.Contact)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Контакт не знайдено")
    return contact

# Маршрут для оновлення контакту по його ідентифікатору
@router.put("/contacts/{contact_id}", response_model=schemas.Contact)
def update_contact(contact_id: int, contact_update: schemas.ContactUpdate, db: Session = Depends(get_db)):
    db_contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Контакт не знайдено")
    for key, value in contact_update.dict(exclude_unset=True).items():
        setattr(db_contact, key, value)
    db.commit()
    db.refresh(db_contact)
    return db_contact

# Маршрут для видалення контакту по його ідентифікатору
@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Контакт не знайдено")
    db.delete(db_contact)
    db.commit()
    return {"message": "Контакт успішно видалено"}

# Маршрут для пошуку контактів за ім'ям, прізвищем або адресою електронної пошти
@router.get("/contacts/search/")
def search_contacts(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    contacts = db.query(models.Contact).filter(
        models.Contact.first_name.ilike(f"%{query}%") |
        models.Contact.last_name.ilike(f"%{query}%") |
        models.Contact.email.ilike(f"%{query}%")
    ).all()
    return contacts

# Маршрут для отримання списку контактів з днями народження в найближчі 7 днів
@router.get("/contacts/birthdays/")
def upcoming_birthdays(db: Session = Depends(get_db)):
    today = datetime.now().date()
    week_later = today + timedelta(days=7)
    upcoming_contacts = []

    # Отримання всіх контактів з бази даних
    all_contacts = db.query(models.Contact).all()

    # Ітерація через всі контакти для перевірки, чи має кожен контакт день народження в найближчій неділі
    for contact in all_contacts:
        if contact.birthday:
            birthday_this_year = datetime(today.year, contact.birthday.month, contact.birthday.day).date()
            if today <= birthday_this_year <= week_later:
                upcoming_contacts.append(contact)

    return upcoming_contacts

# Маршрут для реєстрації користувача
@router.post("/register/", response_model=schemas.User)
async def register_user(user_data: schemas.UserCreate, db: Session = Depends(database.get_db)):
    user = create_user(db, user_data)
    return user

@router.post("/login/")
async def login_user(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неправильний email або пароль")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_jwt_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token}
