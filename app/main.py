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
    df_acti_og = pd.read_csv(file.file, index_col=None)

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

    # Figure 1: plot Proposed vs ActiGraph METs
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x = acti_mets,
        y = wrist_mets,
        mode='markers',
        name='METs'
    ))
    fig1.update_layout(
        title='MET Comparison: Proposed vs ActiGraph',
        xaxis_title='MET (ActiGraph)',
        yaxis_title='MET (Proposed)',
        template='plotly_white'
    )
    plot_div1 = py.offline.plot(fig1, output_type='div')   

    # Figure 2: plot METs trend over timestamp
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=acti_time,
        y=acti_mets,
        mode='lines+markers',
        name='ActiGraph MET'
    ))
    fig2.add_trace(go.Scatter(
        x=wrist_time,
        y=wrist_mets,
        mode='lines+markers',
        name='Proposed/Wrist MET'
    ))
    fig2.update_layout(
        title='METs Trend: ActiGraph vs. Proposed',
        xaxis_title='Time',
        yaxis_title='METs',
        template='plotly_white',
        legend=dict(x=0, y=1.1, orientation='h')
    )
    plot_div2 = py.offline.plot(fig2, output_type='div')   

    # Figure 3: plot cumulative kCal over timestamp
    # weight (for kCal)
    weight_kg = 94.5
    df_acti = pd.DataFrame({'timestamp': acti_time, 'mets': acti_mets})
    df_wrist = pd.DataFrame({'timestamp': wrist_time, 'mets': wrist_mets})
    df_acti['timestamp'] = pd.to_datetime(df_acti['timestamp'])
    df_wrist['timestamp'] = pd.to_datetime(df_wrist['timestamp'])
    df_acti['kcal'] = df_acti['mets'] * 3.5 * weight_kg / 200
    df_wrist['kcal'] = df_wrist['mets'] * 3.5 * weight_kg / 200
    df_acti['cumulative_kcal'] = df_acti['kcal'].cumsum()
    df_wrist['cumulative_kcal'] = df_wrist['kcal'].cumsum()
    final_acti_kcal = df_acti['cumulative_kcal'].iloc[-1]
    final_acti_time = df_acti['timestamp'].iloc[-1]
    final_wrist_kcal = df_wrist['cumulative_kcal'].iloc[-1]
    final_wrist_time = df_wrist['timestamp'].iloc[-1]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df_acti['timestamp'],
        y=df_acti['cumulative_kcal'],
        mode='lines+markers',
        name='ActiGraph Cumulative kCal'
    ))
    fig3.add_trace(go.Scatter(
        x=df_wrist['timestamp'],
        y=df_wrist['cumulative_kcal'],
        mode='lines+markers',
        name='Proposed Cumulative kCal'
    ))
    fig3.add_annotation(
        x=final_acti_time,
        y=final_acti_kcal,
        text=f"{final_acti_kcal:.1f} kcal",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-20,
        font=dict(color="blue")
    )
    fig3.add_annotation(
        x=final_wrist_time,
        y=final_wrist_kcal,
        text=f"{final_wrist_kcal:.1f} kcal",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-20,
        font=dict(color="green")
    )
    fig3.update_layout(
        title='Cumulative Energy Expenditure Over Time',
        xaxis_title='Time',
        yaxis_title='Cumulative kCal',
        template='plotly_white',
        legend=dict(x=0, y=1.1, orientation='h')
    )
    plot_div3 = py.offline.plot(fig3, output_type='div')
    return {'plot1': plot_div1,
            'plot2': plot_div2,
            'plot3': plot_div3}



@app.post("/clear/")
def clear_db(db : Session = Depends(get_db)):
    """
    clear data from db
    """
    db.query(Acti).delete()
    db.query(Wrist).delete()
    db.commit()
