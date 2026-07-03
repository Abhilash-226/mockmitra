from fastapi import FastAPI

app = FastAPI(title="MockMitra API")

@app.get("/")
def root():
    return {"message": "MockMitra API"}
