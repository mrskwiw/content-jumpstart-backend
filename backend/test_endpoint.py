from fastapi import FastAPI
from schemas.project import ProjectCreate

app = FastAPI()

@app.post("/test")
async def test_project(project: ProjectCreate):
    return {"client_id": project.client_id, "name": project.name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
