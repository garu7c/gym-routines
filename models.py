from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class Exercise(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    muscle: str
    difficulty: str
    duration: str
    reps: str
    videoUrl: str
    tips: List[str]

    class Config:
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "Curl de Bíceps",
                "description": "Ejercicio que aísla el bíceps braquial",
                "muscle": "Brazos",
                "difficulty": "Principiante",
                "duration": "3 series",
                "reps": "10-12 repeticiones",
                "videoUrl": "https://www.youtube.com/watch?v=ykJmrZ5v0Oo",
                "tips": ["Mantén los codos cerca del cuerpo"]
            }
        }

class ExerciseInDB(Exercise):
    _id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")