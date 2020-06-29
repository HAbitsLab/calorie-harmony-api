import os
from typing import List
from fastapi import FastAPI, File, UploadFile, Request, Depends, BackgroundTasks
from pydantic import BaseModel  # define schema for API
from fastapi.templating import Jinja2Templates
import pandas as pd
import process
from support_functions import resample, get_intensity, extract_features, get_met_vm3, actigraph_add_datetime
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from models import Acti, Wrist
import plotly as py
from plotly.offline import plot
import plotly.graph_objects as go
from fastapi.middleware.cors import CORSMiddleware


def get_db():
    """
    Make database connection object for sqlite using sql alchemy
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

app = FastAPI()

# Cors middleware
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine) # create sqlalchemy base model objects

templates = Jinja2Templates(directory="templates") # load frontend template


@app.get("/")
def home(request: Request, db : Session = Depends(get_db)):
    """
    Displays the dashboard for wrist ml application
    """
    acti = db.query(Acti).all()
    wrist = db.query(Wrist).all()

    return templates.TemplateResponse("home.html", {
        "request": request,
        "actis": acti,
        "wrists": wrist
    })


def process_acti(file):
    """
    process actical files
    """
    df_acti_og = pd.read_csv(file.file, index_col=None, header=1)

    actigraph_add_datetime(df_acti_og)
    minute_acti = []
    estimation_acti = []
    for i in range(len(df_acti_og)):
        minute_acti.append(df_acti_og['Datetime'][i])
        estimation_acti.append(get_met_vm3(df_acti_og, df_acti_og['Datetime'][i]))
    # save output
    output_acti_df = pd.DataFrame(list(zip(minute_acti, estimation_acti)),
                               columns=['timestamp', 'mets'])
    output_acti_df.to_sql('acti', engine, if_exists='append', index=False)


@app.post("/actifile/")
async def create_upload_file( background_tasks: BackgroundTasks, file: UploadFile = File(...), db : Session = Depends(get_db)):
    """
    upload a single actical file
    """
    background_tasks.add_task(process_acti, file)
    return {"status": "success"}


def process_wrist(files):
    """
    process list of wrist files
    """
    data_list = [] # hold dataframe from gyro and accl wrist csv file
    for wrist_file in files:
        # find and load gyro and accel files, then resample to 20hz
        df_wrist_og = pd.read_csv(wrist_file.file, index_col=None, header=0)
        df_wrist = resample(df_wrist_og, 'Time', 20, 100)
        df_wrist['Datetime'] = pd.to_datetime(df_wrist['Time'], unit='ms', utc=True).dt.tz_convert(
            'America/Chicago').dt.tz_localize(None)
        data_list.append(df_wrist)

    output_wrist_df = process.process_wrist_data(data_list)
    output_wrist_df.to_sql('wrist', engine, if_exists='append', index=False)
        

@app.post("/wristfiles/")
async def create_upload_files(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
    upload multiple wrist files, accl and gyro
    """
    background_tasks.add_task(process_wrist, files)
    return {"status": "success"}


def process_single_wrist(wrist_file):
    """
    process list of wrist files
    Needed to handle each file seperate as 30MB max request size for kestral in Azure
    """
    # find and load gyro and accel files, then resample to 20hz
    df_wrist_og = pd.read_csv(wrist_file.file, index_col=None, header=0)
    df_wrist = resample(df_wrist_og, 'Time', 20, 100)
    df_wrist['Datetime'] = pd.to_datetime(df_wrist['Time'], unit='ms', utc=True).dt.tz_convert(
        'America/Chicago').dt.tz_localize(None)

    output_wrist_df = process.process_wrist_data(df_wrist)
    output_wrist_df.to_sql('wrist', engine, if_exists='append', index=False)


@app.post("/wristfile/")
async def create_upload_wrist(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    upload SINGLE wrist file either accl or gyro
    """
    background_tasks.add_task(process_single_wrist, file)
    return {"status": "success"}


@app.post("/plot/")
def results(db : Session = Depends(get_db)):
    """
    plot the data on graph
    """
    acti = db.query(Acti).all()
    wrist = db.query(Wrist).all()

    acti_time = [i.timestamp for i in acti]
    acti_mets = [i.mets for i in acti]

    wrist_time = [i.timestamp for i in wrist]
    wrist_mets = [i.mets for i in wrist]

    # plot compare
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(x=acti_time, y=acti_mets, mode='markers', name='ActiGraph VM3 Estimation (MET)'))
    fig2.add_trace(
        go.Scatter(x=wrist_time, y=wrist_mets, mode='markers', name='Wrist Estimation (MET)'))
    fig2.update_layout(title='WRIST/Actigraph Compare MET estimate',
                        xaxis_title='Time',
                        yaxis_title='METs Estimate')
    my_plot_div = py.offline.plot(fig2, output_type='div')    
    return {'plot', my_plot_div}


@app.post("/clear/")
"""
clear data from db
"""
def clear_db(db : Session = Depends(get_db)):
    
    db.query(Acti).delete()
    db.query(Wrist).delete()
    db.commit()
