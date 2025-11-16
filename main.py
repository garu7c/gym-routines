from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from models import Exercise
from bson import ObjectId
import os
from dotenv import load_dotenv
import urllib.parse
import time

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

# Conexión a MongoDB - Optimizada para Azure Cosmos DB vCore
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "fitness_db"
COLLECTION_NAME = "exercises"

# Configuración específica para Cosmos DB vCore
try:
    client = AsyncIOMotorClient(
        MONGODB_URL,
        tls=True,
        tlsAllowInvalidCertificates=True,  # Más permisivo para desarrollo
        retryWrites=False,
        maxPoolSize=5,  # Reducido para container
        minPoolSize=1,
        serverSelectionTimeoutMS=30000,  # Timeout más largo
        connectTimeoutMS=30000
    )
    database = client[DATABASE_NAME]
    collection = database[COLLECTION_NAME]
    print("✅ Conectado a MongoDB/Cosmos DB correctamente")
except Exception as e:
    print(f"❌ Error conectando a la base de datos: {e}")
    # No hacemos raise para que la aplicación pueda iniciar
    client = None
    database = None
    collection = None

@app.on_event("startup")
async def startup_event():
    """Inicializar la base de datos"""
    if client is None:
        print("⚠️  Modo sin base de datos - la aplicación funcionará pero sin persistencia")
        return
        
    try:
        # Verificar conexión
        await client.admin.command('ping')
        print("✅ Ping a la base de datos exitoso")
        
        # Crear índice único en el campo 'id' para mejor performance
        await collection.create_index("id", unique=True)
        print("✅ Índice único creado en campo 'id'")
        
        # Contar ejercicios existentes
        count = await collection.count_documents({})
        print(f"✅ Base de datos contiene {count} ejercicios")
            
    except Exception as e:
        print(f"⚠️  Advertencia en startup: {e}")

# Variable temporal para modo sin BD
temp_exercises = []

@app.get("/")
async def root():
    return {
        "message": "Fitness Exercises API", 
        "status": "running",
        "version": "1.0.0",
        "database": "connected" if client else "disconnected"
    }

@app.get("/exercises", response_model=list[Exercise])
async def get_all_exercises():
    """Obtener todos los ejercicios"""
    try:
        if collection:
            exercises = await collection.find().to_list(1000)
            return exercises
        else:
            return temp_exercises
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener ejercicios: {str(e)}")

@app.get("/exercises/{exercise_id}", response_model=Exercise)
async def get_exercise_by_id(exercise_id: int):
    """Obtener un ejercicio por ID"""
    try:
        if collection:
            exercise = await collection.find_one({"id": exercise_id})
            if exercise:
                return exercise
        else:
            # Buscar en memoria
            exercise = next((ex for ex in temp_exercises if ex.get("id") == exercise_id), None)
            if exercise:
                return exercise
        raise HTTPException(status_code=404, detail=f"Exercise with id {exercise_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener ejercicio: {str(e)}")

@app.get("/exercises/muscle/{muscle}", response_model=list[Exercise])
async def get_exercises_by_muscle(muscle: str):
    """Obtener ejercicios por grupo muscular"""
    try:
        if collection:
            # Búsqueda case-insensitive
            exercises = await collection.find({"muscle": {"$regex": muscle, "$options": "i"}}).to_list(1000)
            return exercises
        else:
            # Buscar en memoria
            exercises = [ex for ex in temp_exercises if ex.get("muscle", "").lower() == muscle.lower()]
            return exercises
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar por músculo: {str(e)}")

@app.get("/exercises/difficulty/{difficulty}", response_model=list[Exercise])
async def get_exercises_by_difficulty(difficulty: str):
    """Obtener ejercicios por nivel de dificultad"""
    try:
        if collection:
            exercises = await collection.find({"difficulty": {"$regex": difficulty, "$options": "i"}}).to_list(1000)
            return exercises
        else:
            # Buscar en memoria
            exercises = [ex for ex in temp_exercises if ex.get("difficulty", "").lower() == difficulty.lower()]
            return exercises
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar por dificultad: {str(e)}")

@app.post("/exercises", response_model=Exercise)
async def create_exercise(exercise: Exercise):
    """Crear un nuevo ejercicio"""
    try:
        if collection:
            # Encontrar el próximo ID
            last_exercise = await collection.find_one(sort=[("id", -1)])
            next_id = (last_exercise["id"] if last_exercise else 0) + 1
            
            exercise_dict = exercise.dict()
            exercise_dict["id"] = next_id
            
            result = await collection.insert_one(exercise_dict)
            created_exercise = await collection.find_one({"_id": result.inserted_id})
            return created_exercise
        else:
            # Modo sin BD
            next_id = max([ex.get("id", 0) for ex in temp_exercises] + [0]) + 1
            exercise_dict = exercise.dict()
            exercise_dict["id"] = next_id
            temp_exercises.append(exercise_dict)
            return exercise_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear ejercicio: {str(e)}")

@app.put("/exercises/{exercise_id}", response_model=Exercise)
async def update_exercise(exercise_id: int, exercise: Exercise):
    """Actualizar un ejercicio existente"""
    try:
        if collection:
            # Verificar que el ejercicio existe
            existing_exercise = await collection.find_one({"id": exercise_id})
            if not existing_exercise:
                raise HTTPException(status_code=404, detail=f"Exercise with id {exercise_id} not found")
            
            exercise_dict = exercise.dict()
            exercise_dict["id"] = exercise_id
            
            result = await collection.replace_one({"id": exercise_id}, exercise_dict)
            if result.modified_count == 1:
                updated_exercise = await collection.find_one({"id": exercise_id})
                return updated_exercise
            raise HTTPException(status_code=500, detail="Error al actualizar ejercicio")
        else:
            # Modo sin BD
            exercise_index = next((i for i, ex in enumerate(temp_exercises) if ex.get("id") == exercise_id), None)
            if exercise_index is None:
                raise HTTPException(status_code=404, detail=f"Exercise with id {exercise_id} not found")
            
            exercise_dict = exercise.dict()
            exercise_dict["id"] = exercise_id
            temp_exercises[exercise_index] = exercise_dict
            return exercise_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar ejercicio: {str(e)}")

@app.delete("/exercises/{exercise_id}")
async def delete_exercise(exercise_id: int):
    """Eliminar un ejercicio"""
    try:
        if collection:
            result = await collection.delete_one({"id": exercise_id})
            if result.deleted_count == 1:
                return {"message": "Exercise deleted successfully"}
            raise HTTPException(status_code=404, detail=f"Exercise with id {exercise_id} not found")
        else:
            # Modo sin BD
            global temp_exercises
            initial_count = len(temp_exercises)
            temp_exercises = [ex for ex in temp_exercises if ex.get("id") != exercise_id]
            if len(temp_exercises) < initial_count:
                return {"message": "Exercise deleted successfully"}
            raise HTTPException(status_code=404, detail=f"Exercise with id {exercise_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar ejercicio: {str(e)}")

# Endpoint para health check mejorado
@app.get("/health")
async def health_check():
    """Health check que verifica la conexión a la base de datos"""
    try:
        if client:
            # Verificar conexión a la base de datos
            await client.admin.command('ping')
            count = await collection.count_documents({})
            return {
                "status": "healthy", 
                "database": "connected",
                "total_exercises": count
            }
        else:
            return {
                "status": "healthy", 
                "database": "disconnected",
                "total_exercises": len(temp_exercises),
                "mode": "in-memory"
            }
    except Exception as e:
        return {
            "status": "healthy", 
            "database": "connection_failed",
            "total_exercises": len(temp_exercises),
            "mode": "in-memory",
            "error": str(e)
        }

# Nuevo endpoint para diagnóstico
@app.get("/debug/db")
async def debug_database():
    """Endpoint de diagnóstico para la base de datos"""
    try:
        if client:
            # Test connection
            await client.admin.command('ping')
            count = await collection.count_documents({})
            
            # Obtener algunas estadísticas
            muscles = await collection.distinct("muscle")
            difficulties = await collection.distinct("difficulty")
            
            return {
                "status": "connected", 
                "database": DATABASE_NAME,
                "collection": COLLECTION_NAME,
                "document_count": count,
                "available_muscles": muscles,
                "available_difficulties": difficulties
            }
        else:
            return {
                "status": "disconnected", 
                "mode": "in-memory",
                "document_count": len(temp_exercises),
                "available_muscles": list(set(ex.get("muscle") for ex in temp_exercises)),
                "available_difficulties": list(set(ex.get("difficulty") for ex in temp_exercises))
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Nuevo endpoint para probar conexión específica
@app.get("/test-connection")
async def test_connection():
    """Probar específicamente la conexión a MongoDB"""
    try:
        if client:
            # Probar operación simple
            start_time = time.time()
            await client.admin.command('ping')
            ping_time = time.time() - start_time
            
            # Probar contar documentos
            count = await collection.count_documents({})
            
            return {
                "status": "success",
                "message": "Conexión a MongoDB exitosa",
                "ping_time_ms": round(ping_time * 1000, 2),
                "document_count": count,
                "connection_string": MONGODB_URL[:50] + "..." if len(MONGODB_URL) > 50 else MONGODB_URL
            }
        else:
            return {
                "status": "error",
                "message": "Cliente MongoDB no inicializado",
                "connection_string": MONGODB_URL
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error de conexión: {str(e)}",
            "connection_string": MONGODB_URL
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)