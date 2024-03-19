from fastapi import FastAPI
from contactpr import routes

app = FastAPI()

app.include_router(routes.router)
