import os 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from sklearn import preprocessing
import inspect
import sys



def resample(dataDf, timeColHeader, samplingRate, gapTolerance=np.inf, fixedTimeColumn=None):
    """
    Parameters
    ----------
    dataDf : data dataframe, contains unixtime column and data column(s)

    timeColHeader : string, time column header

    samplingRate : int
        Number of samples per second

    gapTolerance: int(ms)
        if the distance between target point and either of the neighbors is further than gapTolerance in millisecond,
        then interpolation is nan
        if gapTolerance=0, the gapTolerance rule will not exist

    fixedTimeColumn:

    Examples
    --------
    >>> timeColHeader = 'unixtime'
    >>> df = pd.DataFrame(np.arange(20).reshape(5,4),
                      columns=['unixtime', 'A', 'B', 'C'])

    >>> unix = np.array([1500000000000,1500000000048,1500000000075,1500000000100,1500000000150])
    >>> df['unixtime'] = unix
    >>> print(df)
            unixtime   A   B   C
    0  1500000000000   1   2   3
    1  1500000000048   5   6   7
    2  1500000000075   9  10  11
    3  1500000000100  13  14  15
    4  1500000000150  17  18  19
    >>> newSamplingRate = 20
    >>> newDf = resample(df, timeColHeader, newSamplingRate)
    >>> print(newDf)
            unixtime          A          B          C
    0  1500000000000   1.000000   2.000000   3.000000
    1  1500000000050   5.296295   6.296295   7.296295
    2  1500000000100  13.000000  14.000000  15.000000
    3  1500000000150  17.000000  18.000000  19.000000

    >>> newSamplingRate = 33
    >>> newDf = resample(df, timeColHeader, newSamplingRate)
    >>> print(newDf)
            unixtime          A          B          C
    0  1500000000000   1.000000   2.000000   3.000000
    1  1500000000030   3.525238   4.525238   5.525238
    2  1500000000060   6.867554   7.867554   8.867554
    3  1500000000090  11.545441  12.545441  13.545441
    4  1500000000121  14.696960  15.696960  16.696960

    (Note: the 5th unixtime is 1500000000121 instead of 1500000000120, since 5th sampling is 121.21212121ms after 1st sampling.
    
    development log:
    1.
    # always take the first timestamp time[0]
    # if starttime == None:
    newSignalList = [signalArr[0]]
    newUnixtimeList = [unixtimeArr[0]]
    # else:
    #     newUnixtimeList = [starttime]
        # if starttime >= signalArr[0]
        # newSignalList = interpolate(unixtimeArr[tIndAfter-1], signalArr[tIndAfter-1], unixtimeArr[tIndAfter], signalArr[tIndAfter], t)
    
    2.
    # if gapTolerance == 0 or \
    #     ((abs(unixtimeArr[tIndAfter-1]-t)<=gapTolerance) and \
    #     (abs(unixtimeArr[tIndAfter]-t)<=gapTolerance)):

    if gapTolerance == 0 or \
        (abs(unixtimeArr[tIndAfter-1]-unixtimeArr[tIndAfter])<=gapTolerance):

    -----
    """

    originalNameOrder = list(dataDf.columns.values)

    unixtimeArr = dataDf[timeColHeader].values
    deltaT = 1000.0/samplingRate
    
    dataDf = dataDf.drop(timeColHeader, axis=1)
    dataArr = dataDf.values
    names = list(dataDf.columns.values)

    n = len(unixtimeArr)
    newDataList = []
    
    if n<2:
        return

    if fixedTimeColumn is None:
        #Looping through columns to apply the resampling method for each column
        for c in range(dataArr.shape[1]):
            signalArr = dataArr[:,c]

            # always take the first timestamp time[0]
            newSignalList = [signalArr[0]]
            newUnixtimeList = [unixtimeArr[0]]

            t = unixtimeArr[0] + deltaT
            tIndAfter = 1

            # iterate through the original signal
            while True:
                # look for the interval that contains 't'
                i0 = tIndAfter
                for i in range(i0,n):# name indBefore/after
                    if  t <= unixtimeArr[i]:#we found the needed time index
                        tIndAfter = i
                        break

                # interpolate in the right interval, gapTolenance=0 means inf tol,
                if gapTolerance == 0 or \
                    (abs(unixtimeArr[tIndAfter-1]-unixtimeArr[tIndAfter])<=gapTolerance):
                    s = interpolate(unixtimeArr[tIndAfter-1], signalArr[tIndAfter-1], \
                                    unixtimeArr[tIndAfter], signalArr[tIndAfter], t)
                else:
                    s = np.nan

                # apppend the new interpolated sample to the new signal and update the new time vector
                newSignalList.append(s)
                newUnixtimeList.append(int(t))
                # take step further on time
                t = t + deltaT
                # check the stop condition
                if t>unixtimeArr[-1]:
                    break

            newDataList.append(newSignalList)
            newDataArr = np.transpose(np.array(newDataList))

        dataDf = pd.DataFrame(data = newDataArr, columns = names)
        dataDf[timeColHeader] = np.array(newUnixtimeList)

        # change to the original column order
        dataDf = dataDf[originalNameOrder]

    else:  #if fixedTimeColumn not None:
        #Looping through columns to apply the resampling method for each column
        for c in range(dataArr.shape[1]):
            signalArr = dataArr[:,c]
            newSignalList = []
            newUnixtimeList = []

            iFixedTime = 0

            t = fixedTimeColumn[iFixedTime]
            tIndAfter = 0
            outOfRange = 1

            # iterate through the original signal
            while True:
                # look for the interval that contains 't'
                i0 = tIndAfter
                for i in range(i0,n):
                    if  t <= unixtimeArr[i]:#we found the needed time index
                        tIndAfter = i
                        outOfRange = 0
                        break

                if outOfRange:
                    s = np.nan
                else:
                    # interpolate in the right interval
                    if tIndAfter == 0: # means unixtimeArr[0] > t, there is no element smaller than t
                        s = np.nan
                    elif gapTolerance == 0 or \
                        (abs(unixtimeArr[tIndAfter-1] - unixtimeArr[tIndAfter]) <= gapTolerance):
                        s = interpolate(unixtimeArr[tIndAfter-1], signalArr[tIndAfter-1], \
                                        unixtimeArr[tIndAfter], signalArr[tIndAfter], t)
                    else:
                        s = np.nan

                # apppend the new interpolated sample to the new signal and update the new time vector
                newSignalList.append(s)
                newUnixtimeList.append(int(t))

                # check the stop condition
                if t>unixtimeArr[-1]:
                    break
                # take step further on time
                iFixedTime += 1

                if iFixedTime>=len(fixedTimeColumn):
                    break
                t = fixedTimeColumn[iFixedTime]

            newDataList.append(newSignalList)
            newDataArr = np.transpose(np.array(newDataList))

        dataDf = pd.DataFrame(data = newDataArr, columns = names)
        dataDf[timeColHeader] = np.array(newUnixtimeList)

        # change to the original column order
        dataDf = dataDf[originalNameOrder]
    return dataDf

def interpolate(t1, s1, t2, s2, t):
    """Interpolates at parameter 't' between points (t1,s1) and (t2,s2)
    """

    if(t1<=t and t<=t2): #we check if 't' is out of bounds (between t1 and t2)
        m = float(s2 - s1)/(t2 - t1)
        b = s1 - m*t1
        return m*t + b
    else:
        return np.nan


def clean_and_sort(df):

    df = df.apply(pd.to_numeric, errors='coerce')
    df.dropna(inplace=True)
    df.sort_values("Time", inplace=True)
    df.drop_duplicates(subset=['Time'], inplace=True)
    df = df[(df['Time'] > 1000000000000) & (df['Time'] < 10000000000000)]

    return df

def organize(df, output_path, subj, sensor, location, resampled=False):

    if resampled:
        resample_folder = "Resampled"
    else:
        resample_folder = "Not Resampled"

    df['DT'] = pd.to_datetime(pd.to_datetime(df['Time'], unit='ms', utc=True).dt.tz_convert('US/Central'))
	#df['Month'] = df['DT'].dt.to_period('M')
	#df['Day'] = df['DT'].dt.to_period('D')

    df['Hour'] = df['DT'].dt.to_period('H')

    for date in df['Hour'].unique():
        path = os.path.join(output_path, subj, location, 'Wrist', 'Clean', resample_folder, sensor, '{}-{}-{}'.format(date.year,date.month,date.day), str(date.hour))
        if not os.path.exists(path):
            os.makedirs(path)
        df_hour = df[df['Hour'] == date]
        df_hour.to_csv(os.path.join(path, 'accel_data.csv'), index=False)

def clean_and_resample(output_path, subjs, location):
    for subj in subjs:
        print("Cleaning {}...".format(subj))

        accel_df = pd.read_csv(os.path.join(output_path, subj, location, 'Wrist', 'Aggregated', 'Accelerometer', 'Accelerometer.csv'), usecols=[0,1,2,3])
        gyro_df = pd.read_csv(os.path.join(output_path, subj, location, 'Wrist', 'Aggregated', 'Gyroscope', 'Gyroscope.csv'), usecols=[0,1,2,3])

        accel_df = clean_and_sort(accel_df)
        gyro_df = clean_and_sort(gyro_df)

        accel_df.to_csv(os.path.join(output_path, subj, location, 'Wrist', 'Aggregated', 'Accelerometer', 'Accelerometer.csv'), index=False)
        gyro_df.to_csv(os.path.join(output_path, subj, location, 'Wrist', 'Aggregated', 'Gyroscope', 'Gyroscope.csv'), index=False)

        print("Done cleaning {}.".format(subj))

        print("Resampling {}...".format(subj))

        accel_df_resampled = resample(accel_df, "Time", 20, gapTolerance=500).dropna()
        gyro_df_resampled = resample(gyro_df, "Time", 20, gapTolerance=500).dropna()

        print("Done Resampling {}.".format(subj))

        print("Organizing {}...".format(subj))

        organize(accel_df, output_path, subj, 'Accelerometer', location)
        organize(gyro_df, output_path, subj, 'Gyroscope', location)

        organize(accel_df_resampled, output_path, subj, 'Accelerometer', location, resampled=True)
        organize(gyro_df_resampled, output_path, subj, 'Gyroscope', location, resampled=True)

        print("Done Organizing {}.".format(subj))


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

def process_wrist(df_wrist):
    df_wrist['Datetime'] = pd.to_datetime(df_wrist['Time'], unit='ms', utc=True).dt.tz_convert(
            'America/Chicago').dt.tz_localize(None)
    return(df_wrist)

def get_freq_intensity(df, fs, top, plot=False):
    df_temp = df.dropna()
    acc_x = list(df_temp['accX'])
    acc_y = list(df_temp['accY'])
    acc_z = list(df_temp['accZ'])
    y = []
    if(len(acc_x) != 0):
        for i in range(1, len(acc_x)):
            y.append(np.sqrt(acc_x[i]**2 + acc_y[i]**2 + acc_z[i]**2))   
            n = len(y) # length of the signal
            k = np.arange(n)
            T = n/fs
            frq = k/T # two sides frequency range
            frq = frq[:len(frq)//2] # one side frequency range
            Y = np.fft.fft(y)/n # dft and normalization
            Y = Y[:n//2]   
            
        if(plot):
            plt.figure(figsize=(10,6))
            plt.plot(frq[1:],abs(Y[1:])) # plotting the spectrum without 0Hz
            plt.xlabel('Freq (Hz)')
            plt.ylabel('|Y(freq)|')

        top = top + 1
        fr = list(abs(Y))
        result = frq[fr.index(sorted(fr,reverse=True)[:top][top-1])]
        return(result)
    else:
        return np.nan

def get_rmssd(df, norm = 'l2'):
    df_temp = df.dropna()
    acc_x = list(df_temp['accX'])
    acc_y = list(df_temp['accY'])
    acc_z = list(df_temp['accZ'])
    data = np.array([df_temp['accX'], df_temp['accY'], df_temp['accZ']])

    if(len(acc_x) != 0):
        if(norm == 'l2'):
            processed = preprocessing.normalize(data, norm='l2')
            acc_x = processed[0]
            acc_y = processed[1]
            acc_z = processed[2]
        if(norm == 'l1'):
            processed = preprocessing.normalize(data, norm='l1')
            acc_x = processed[0]
            acc_y = processed[1]
            acc_z = processed[2]
        if(norm == 'minmax'):
            scaler = MinMaxScaler()
            scaler.fit(data)
            processed = scaler.transform(data)
            acc_x = processed[0]
            acc_y = processed[1]
            acc_z = processed[2]
            
        temp_sum = 0
        for i in range(1, len(acc_x)):
            temp_sum = temp_sum + (acc_x[i] - acc_x[i - 1])**2 + (acc_y[i] - acc_y[i - 1])**2 + (acc_z[i] - acc_z[i - 1])**2
        rmssd = (temp_sum/len(acc_x))**(1/2)
        return(rmssd)
    else:
        return np.nan
    
def get_train_data(df, st, window_size, input_type='gyro'):
    et = st + pd.DateOffset(minutes=window_size/60)
    temp = df.loc[(df['Datetime'] >= st) & (df['Datetime'] < et)].reset_index(drop=True)
    if(input_type == 'gyro'):
        this_min_data = [temp['rotX'], temp['rotY'], temp['rotZ']]
    elif(input_type == 'acc'):
        this_min_data = [temp['accX'], temp['accY'], temp['accZ']]
    else:
        print('Invalid input data type')
        return
    return(this_min_data)

def extract_features(data):
    # Added new features: Median, mean, maximum, minimum, range, standard deviation, and root mean square power

    outcome = []
    for m in data:
        temp = []
        try:
            temp.append(np.median(m,axis=1))
            temp.append(np.mean(m,axis=1))
            temp.append(np.max(m,axis=1))
            temp.append(np.min(m,axis=1))
            temp.append(np.max(m,axis=1) - np.min(m,axis=1))
            temp.append(np.std(m,axis=1))
            temp.append(np.sqrt(np.mean(m**2, axis=1)))
            temp = np.concatenate(temp)
        except:
            temp = np.array([0] * 42)
        outcome.append(temp)
    return np.array(outcome)