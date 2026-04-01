from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "서버 정상 작동"}

@app.get("/test")
def test():
    return {"message": "테스트 성공"}