import os
import joblib
import numpy as np
import pandas as pd
from datetime import timedelta
from support_functions import get_intensity, extract_features, get_met_vm3, actigraph_add_datetime


DATA_LENGTH = 1200


def process_wrist_data(wrist_data):
    """
    Process the wrist data from input files
    :param wrist_data: list dataframe
        gyro and acceleromtere dataframe from input csv files
    :return: dataframe
        process and minute met estimate from wrist worn device using preloaded model
    """
    # load the pre-trained model
    path_model = os.path.join(os.getcwd(), 'xgbc.dat')
    model = joblib.load(path_model)

    if len(wrist_data) != 2:  # not two files uploaded
        print("Incorrect file count")
        # TODO: log error, alert user in api get
        return 1
    else:
        for df in wrist_data:  # check columns names in df for gyro vs accel
            if "accX" in df.columns:
                df_accel = df
            elif "rotX" in df.columns:
                df_gyro = df
            else:
                print("error in data frame columns")
                # TODO: log error, alert user in api get
                return 1
        if df_accel.empty or df_gyro.empty:
            print("error in missing data frame")
            # TODO: log error, alert user in api get
            return 1

    st_ceil, et_floor = time_parameters(df_gyro)

    minute_wrist = []
    estimation_wrist = []
    start_time = st_ceil

    # Examine each minute
    for i in range(int((et_floor - st_ceil).seconds / 60)):
        minute_wrist.append(start_time)
        end_time = start_time + pd.DateOffset(minutes=1)

        model_estimation = model_estimate_accl(df_accel, start_time, end_time)

        features = model_features_gyro(df_gyro, start_time, end_time)
        if features.size == 0:
            model_classification = -1
        else:
            model_output = model.predict(features)
            model_classification = model_output[0]

        model_estimation = get_model_classification(model_classification, model_estimation)

        estimation_wrist.append(model_estimation)

        start_time += pd.DateOffset(minutes=1)
        # save output
    output_wrist_df = pd.DataFrame(list(zip(minute_wrist, estimation_wrist)),
                                   columns=['Time', 'Wrist Estimation (MET)'])
    output_wrist_df = output_wrist_df.fillna('')  # Change the NaN to empty
    return output_wrist_df


def process_acti_data(df_acti):
    """
    Process input actigrapph csv file to produce data frame with time series mets estimates
    :param df_acti: data frame
        input structured data frame from actigraph device
    :return: dataframe
        process and minute met estimate from actigraph data
    """
    actigraph_add_datetime(df_acti)
    minute_acti = []
    estimation_acti = []
    for i in range(len(df_acti)):
        minute_acti.append(df_acti['Datetime'][i])
        estimation_acti.append(get_met_vm3(df_acti, df_acti['Datetime'][i]))

    # save output
    output_acti_df = pd.DataFrame(list(zip(minute_acti, estimation_acti)),
                               columns=['Time', 'ActiGraph VM3 Estimation (MET)'])
    return output_acti_df


def time_parameters(df):
    """
    Set start and end times for wrist data
    :param df: data frame
            input data frame to calculate time parameters
    :return: st_ceil, et_floor:
            start ceiling and end time floor
    """
    st = df['Datetime'][0]
    et = df['Datetime'][len(df) - 1]
    st_ceil = st - timedelta(minutes=st.minute % 10,
                             seconds=st.second,
                             microseconds=st.microsecond)
    st_ceil = st_ceil + pd.DateOffset(minutes=1)
    et_floor = et - timedelta(minutes=et.minute % 10,
                              seconds=et.second,
                              microseconds=et.microsecond)
    return st_ceil, et_floor


def model_estimate_accl(df_accel, start_time, end_time):
    """
    model estimate using acceleration signal

    :param df_accel:
        acceleration data frame from input csv
    :param start_time:
    :param end_time:
    :return: model strimation
        mets estimate from model
    """
    temp_accel = df_accel.loc[
        (df_accel['Datetime'] >= start_time) & (df_accel['Datetime'] < end_time)].reset_index(drop=True)

    model_estimation = get_intensity(df_accel, start_time) * 0.39212 + 1.3  # TODO: Where did these come from?
    if sum(pd.isnull(temp_accel['accX'])) > (DATA_LENGTH / 10):
        model_estimation = np.nan

    return model_estimation


def model_features_gyro(df_gyro, start_time, end_time):
    """
    Extract features from the gyro signal
    :param df_gyro:
    :param start_time:
    :param end_time:
    :return:
    """
    temp_gyro = df_gyro.loc[
        (df_gyro['Datetime'] >= start_time) & (df_gyro['Datetime'] < end_time)].reset_index(drop=True)

    if len(temp_gyro['rotX']) == DATA_LENGTH:
        this_min_gyro = [temp_gyro['rotX'], temp_gyro['rotY'], temp_gyro['rotZ']]
        if sum(np.isnan(this_min_gyro[0])) < (DATA_LENGTH / 10):
            features = extract_features([this_min_gyro])
        else:
            features = np.array([])
    else:
        features = np.array([])
    return features


def get_model_classification(model_classification, model_estimation):
    """
    Set model estimation from classification and thresholds
    :param model_classification:
        classifiaction with model and gyro
    :param model_estimation:
        model estimation with accel
    :return: model estimation
        model estimation of mets
    """
    if model_classification == -1:
        if model_estimation < 1:
            model_estimation = 1
    elif model_classification == 0:
        if model_estimation < 1:
            model_estimation = 1
        elif model_estimation > 1.5:
            model_estimation = 1.5
    elif model_classification == 1:
        if model_estimation < 1.5:
            model_estimation = 1.5
    return model_estimation
