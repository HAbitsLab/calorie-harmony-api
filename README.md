# Web API to compare Calorie Estimates between a Smartwatch and Actigraphy

A project to demonstrate the WRIST algorithm API. To compare calorie estimates between the actigraphy and a smart watch.

The user is able to upload files for each device, the frontend web app will produce tables showing the calculated calorie estimate for each device and will plot the data.

> Sample data is provide in this repo to test is the  [/data directory](data)

### Running the Wrist ML web app:

A public docker image is available to test locally:
 
```docker run -d -p 80:80 habitslab/wristapi```

This will pull the docker image and start a container on the local machine.
The web app will be available at ```localhost```

![Wrist app1](/images/app-1.jpg)

The user will select the correct .CSV files with the **choose file** button.

Then **Load Data** button will produce the table of minute epochs and mets estimate.

The actigraph requires the actigraph.csv file

The wrist data requires **2 files: accelerometer.csv and gyroscope.csv**
Loading data in the wrist section processes the files with the *WRIST* algorithm
> This process will take a few minutes. **Do not refresh page during processing this will stop the process**

![Wrist app2](/images/app-2.jpg)

![Wrist app3](/images/app-3.jpg)

Once the processing of the .CSV files is complete the met estimate table will be populated.

![Wrist app4](/images/app-4.jpg)

The user is able to plot the data from these tables with the **Plot Data** button

![Wrist app5](/images/app-5.jpg)

If the user would like to run though the process with other files the **Clear Data** button at the top of the page removes data from the tables and new data is able to be loaded. 



