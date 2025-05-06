import joblib
import numpy as np
import pandas as pd
from datetime import timedelta
from util import time_parameters, process_wrist, get_freq_intensity, get_rmssd, get_train_data, extract_features, resample
from xgboost import XGBClassifier
from support_functions import get_intensity#, extract_features

DATA_LENGTH = 1200
WRIST_DATA = []


def upload_single_wrist(wrist_df):
    WRIST_DATA.append(wrist_df)


def process_wrist_data(wrist_data):
    """
    Process the wrist data from input files
    :param wrist_data: list dataframe
        gyro and acceleromtere dataframe from input csv files
    :return: dataframe
        process and minute met estimate from wrist worn device using preloaded model
    """
    # load the pre-trained model
    # classification model
    model_classification = XGBClassifier()
    model_classification.load_model("./classification_model.json")
    # regression model
    loaded_rf = joblib.load("./regression_model.joblib")

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

    df_acc_resampled = resample(df_accel[['Time', 'accX', 'accY', 'accZ']], 'Time', 20)
    df_gyro_resampled = resample(df_gyro[['Time', 'rotX', 'rotY', 'rotZ']], 'Time', 20)

    # add datetime from Unix timestamp
    df_acc = process_wrist(df_acc_resampled)
    df_gyro = process_wrist(df_gyro_resampled)

    # normalize each column to match the scale from original data
    targets = ['accX', 'accY', 'accZ']
    min_max = {'accX': [38.03060682003315, -33.763857951531044],
               'accY': [34.77019433156978, -43.30149280531167],
               'accZ': [37.98169060088745, -36.9844767541086]}

    for each_col in targets:
        max_old = np.max(df_acc[each_col])
        min_old = np.min(df_acc[each_col])
        value = df_acc[each_col]
        max_acc = min_max[each_col][0]
        min_acc = min_max[each_col][1]
        df_acc[each_col] = (max_acc - min_acc) / (max_old - min_old) * (value - max_old) + max_acc

    # segmentation and feature extraction
    st_ceil, et_floor = time_parameters(df_gyro)  # get start and end time of gyroscope

    window_size = 60
    minute_wrist = []
    l_intensity_freq = []
    l_intensity_rmssd_l1 = []
    data_training = []

    start_time = st_ceil

    # Examine each minute
    for i in range(int((et_floor - st_ceil).seconds / 60)):
        minute_wrist.append(start_time)
        end_time = start_time + pd.DateOffset(minutes=1)

        temp = df_acc.loc[(df_acc['Datetime'] >= start_time) & (df_acc['Datetime'] < end_time)].reset_index(drop=True)
        l_intensity_freq.append(get_freq_intensity(temp, 100, 1, False))
        l_intensity_rmssd_l1.append(get_rmssd(temp, norm='l1'))

        data_training.append(
            get_train_data(df_gyro, start_time, window_size, 'gyro') + get_train_data(df_acc, start_time, window_size,
                                                                                      'acc'))
        start_time += pd.DateOffset(minutes=1)

    for i in range(len(data_training)):
        for j in range(6):
            if (data_training[i][j].shape[0] != window_size * 20):
                s_temp = pd.Series([0] * int(window_size * 20 - data_training[i][j].shape[0]))
                data_training[i][j] = pd.concat([data_training[i][j], s_temp], ignore_index=True)

    np_training = np.array(data_training)
    data_train = extract_features(np_training)

    estimation = []
    # 1st stage classification
    classification = model_classification.predict(data_train)

    # Need Demographic info
    gender = 1.0
    age = 34
    BMI = 36

    # 2nd stage regression
    for i in range(len(classification)):
        if (classification[i] == 0):
            estimation.append(1.0)
        else:
            # complete feature for regression model (TODO)
            # 'gender', 'age', 'BMI', 'Intensity (Freq)', 'gender_age','gender_BMI','age_BMI','age_gender_BMI', 'Intensity (RMSSD_l1)'
            feature_complete = [gender, age, BMI] + [l_intensity_freq[i]] + [gender * age, gender * BMI, age * BMI,
                                                                             age * gender * BMI] + [
                                   l_intensity_rmssd_l1[i]]
            estimation.append(loaded_rf.predict(np.array(feature_complete).reshape(1, 9))[0])

    print("Done Processing Wrist")
    return pd.DataFrame({'timestamp':minute_wrist, 'mets':estimation})


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


def set_realistic_met_estimates(model_classification, model_estimation):
    """
    Set realistic model estimates for mets
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
