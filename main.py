from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from models import Exercise, ExerciseInDB
from bson import ObjectId
import os
from dotenv import load_dotenv
import json

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Fitness Exercises API",
    description="Microservicio para gestionar ejercicios de fitness",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a MongoDB
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "fitness_db"
COLLECTION_NAME = "exercises"

client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]
collection = database[COLLECTION_NAME]

# Datos iniciales
initial_exercises = [
    {
        "id": 1,
        "name": "Curl de Bíceps",
        "description": "Ejercicio que aísla el bíceps braquial, trabajando también el braquial y braquiorradial.",
        "muscle": "Brazos",
        "difficulty": "Principiante",
        "duration": "3 series",
        "reps": "10-12 repeticiones",
        "videoUrl": "https://www.youtube.com/watch?v=ykJmrZ5v0Oo",
        "tips": [
            "Mantén los codos cerca del cuerpo durante todo el movimiento.",
            "No balancees el cuerpo para levantar las pesas.",
            "Controla el movimiento tanto al subir como al bajar las mancuernas.",
            "Concentrate en la contracción del bíceps."
        ]
    },
    {
        "id": 2,
        "name": "Fondos en Paralelas",
        "description": "Ejercicio compuesto que trabaja principalmente el tríceps, pectorales y deltoides anterior.",
        "muscle": "Brazos",
        "difficulty": "Intermedio",
        "duration": "3-4 series",
        "reps": "8-12 repeticiones",
        "videoUrl": "https://www.youtube.com/watch?v=2z8JmcrW-As",
        "tips": [
            "Inclina ligeramente el torso hacia adelante para activar más el tríceps.",
            "Baja hasta sentir estiramiento en el pecho.",
            "Empuja hacia arriba con fuerza, extendiendo completamente los brazos."
        ]
    },
    {
        "id": 3,
        "name": "Extensiones de Tríceps con Mancuerna",
        "description": "Ejercicio que aísla el tríceps braquial.",
        "muscle": "Brazos",
        "difficulty": "Intermedio",
        "duration": "3 series",
        "reps": "12-15 repeticiones",
        "videoUrl": "https://www.youtube.com/watch?v=nRiJVZDpdL0",
        "tips": [
            "Mantén los codos cerca de la cabeza durante todo el movimiento.",
            "Controla el movimiento tanto al subir como al bajar la mancuerna.",
            "Evita arquear la espalda durante el ejercicio.",
            "Concentrate en la contracción del tríceps."
        ]
    }
]

@app.on_event("startup")
async def startup_event():
    """Inicializar la base de datos con datos de ejemplo"""
    count = await collection.count_documents({})
    if count == 0:
        await collection.insert_many(initial_exercises)
        print("Datos iniciales insertados")

@app.get("/")
async def root():
    return {"message": "Fitness Exercises API", "status": "running"}

@app.get("/exercises", response_model=list[Exercise])
async def get_all_exercises():
    """Obtener todos los ejercicios"""
    exercises = await collection.find().to_list(1000)
    return exercises

@app.get("/exercises/{exercise_id}", response_model=Exercise)
async def get_exercise_by_id(exercise_id: int):
    """Obtener un ejercicio por ID"""
    exercise = await collection.find_one({"id": exercise_id})
    if exercise:
        return exercise
    raise HTTPException(status_code=404, detail="Exercise not found")

@app.get("/exercises/muscle/{muscle}", response_model=list[Exercise])
async def get_exercises_by_muscle(muscle: str):
    """Obtener ejercicios por grupo muscular"""
    exercises = await collection.find({"muscle": {"$regex": muscle, "$options": "i"}}).to_list(1000)
    return exercises

@app.get("/exercises/difficulty/{difficulty}", response_model=list[Exercise])
async def get_exercises_by_difficulty(difficulty: str):
    """Obtener ejercicios por nivel de dificultad"""
    exercises = await collection.find({"difficulty": {"$regex": difficulty, "$options": "i"}}).to_list(1000)
    return exercises

@app.post("/exercises", response_model=Exercise)
async def create_exercise(exercise: Exercise):
    """Crear un nuevo ejercicio"""
    # Encontrar el próximo ID
    last_exercise = await collection.find_one(sort=[("id", -1)])
    next_id = (last_exercise["id"] if last_exercise else 0) + 1
    
    exercise_dict = exercise.dict()
    exercise_dict["id"] = next_id
    
    result = await collection.insert_one(exercise_dict)
    created_exercise = await collection.find_one({"_id": result.inserted_id})
    return created_exercise

@app.put("/exercises/{exercise_id}", response_model=Exercise)
async def update_exercise(exercise_id: int, exercise: Exercise):
    """Actualizar un ejercicio existente"""
    exercise_dict = exercise.dict()
    exercise_dict["id"] = exercise_id
    
    result = await collection.replace_one({"id": exercise_id}, exercise_dict)
    if result.modified_count == 1:
        updated_exercise = await collection.find_one({"id": exercise_id})
        return updated_exercise
    raise HTTPException(status_code=404, detail="Exercise not found")

@app.delete("/exercises/{exercise_id}")
async def delete_exercise(exercise_id: int):
    """Eliminar un ejercicio"""
    result = await collection.delete_one({"id": exercise_id})
    if result.deleted_count == 1:
        return {"message": "Exercise deleted successfully"}
    raise HTTPException(status_code=404, detail="Exercise not found")

# Endpoint para health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)