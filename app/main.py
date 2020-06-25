import os
from typing import List
from fastapi import FastAPI, File, UploadFile, Request, BackgroundTasks
from pydantic import BaseModel  # define schema for JSON
from fastapi.templating import Jinja2Templates
import pandas as pd
import process
from support_functions import resample, get_intensity, extract_features, get_met_vm3, actigraph_add_datetime


class Input(BaseModel):
    age: int
    gender: str
    BMI: float


app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.post("/")

@app.get("/")
def home(request: Request):
    """
    Displays the dashboard for wrist ml application
    """
    return templates.TemplateResponse("home.html", {
        "request": request,
        "somevar": 2,
    })

@app.post("/post")
def post_data():
    """
    posts data to post
    """
    return {"code":"success",
            "message": "posted success"}

@app.put("/predictmets")
def predict_complex_model(d:Input):
    if d.age > 35 or d.sex == 'F' :
        return {'survived':1}
    else:
        return {'survived':0}



@app.post("/files/")
async def create_file(file: bytes = File(...)):
    return {"file_size": len(file)}


@app.post("/actifile/")
def create_upload_file(file: UploadFile = File(...)):
    """
    upload a single actical file
    """
    df_acti_og = pd.read_csv(file.file, index_col=None, header=1)
    mets_estimate = process.process_acti_data(df_acti_og)
    return {"filename": file.filename,
            "data": mets_estimate}


@app.post("/wristfiles/")
async def create_upload_files(files: List[UploadFile] = File(...)):
    data_list = [] # hold dataframe from gyro and accl wrist csv file
    for wrist_file in files:
        # find and load gyro and accel files, then resample to 20hz
        print(wrist_file.filename)
        df_wrist_og = pd.read_csv(wrist_file.file, index_col=None, header=0)
        df_wrist = resample(df_wrist_og, 'Time', 20, 100)
        df_wrist['Datetime'] = pd.to_datetime(df_wrist['Time'], unit='ms', utc=True).dt.tz_convert(
            'America/Chicago').dt.tz_localize(None)
        data_list.append(df_wrist)

    mets_estimate = process.process_wrist_data(data_list)
    return {"data": mets_estimate}

