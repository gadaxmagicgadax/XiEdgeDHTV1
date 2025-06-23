# Xi IoT Weather station

## Overview

This work has been carried out starting from the original PoC written and tested by Emil Nilsson ([https://github.com/voxic/XiEdgeKafkaWeatherStationV2](https://github.com/voxic/XiEdgeKafkaWeatherStationV2))

This solution ingests weather data from a weather station based on ESP32 DHT11 sensor for temperature and humidity and Ublox Neo-6m GPS receiver.

!["ESP32"](ESP32-DHT-UBlox-LCD.png)

ESP32 connects to internet via my iPhone and send sensor and GPS data to Nutanix Karbon Platform Services via MQTT protocol. Code in ESP32 is in micropython. LCD display has been used for testing purposes.

To make it work you have to define the sensor in Karbon Platform Services and get the appropriate certificates to connect and send data. See [here](https://github.com/gadaxmagicgadax/DHTmqttNutanixIoT) for the details of the breadboard project.

So , data is ingested using MQTT, the incoming weather data is in this format:

`{"measurement":"weather", "tags": { "Area": "Italy", "Location": "Aprilia" }, "fields": {"temperature" : "25","humidity" : "52","latitude" : "41.79642","longitude" : "12.42329","altitude" : "76.4"}}`

Such format is prepared by the micropython code in the ESP32 and ready to be sent to the InfluxDB. Data is then sent to a Kafka topic using the Data Pipeline. Three containerized applications are then deployed to consume data from Kafka, input the data to Influx DB and graphing using Grafana.

!["Overview"](overview.png)

## Step by step guide

Simple step by step guide for setting up the Xi IoT Weather station using Xi IoT Portal.

## Step 1 - Create a project

Sign in to the Xi IoT Portal. Open the ```Projects``` section in the menu on the left. Click on ```Create```.
Give your project a name and assign a user.Click ```Next```. Assign a service domain using ```Add service domain```.Click ```Next```. Enable services for our project.This project is making use of

* Kubernetes Apps
* Functions and Data Pipelines
* Ingress Controller - Traefik
* Data Streaming - Kafka, NATS

Click on ```Create```.

## Step 2 - Setup data source

Next we add a new data source. This is where the data enters the Xi IoT solution.
We will create a new category for our incoming data.
Open the ```Categories``` section in the menu and click ```Create```. Give the new category a name and click on ```Add value```. In my example I use ```IncommingData``` as name and add a value of ```weather```

!["Category"](category.png)

Once we have our category setup we can add the data source.

Open the ```Data sources and IoT sensors``` section of the menu. Click on ```Add Data source```.
Select ```sensor```, Give the data source a Name, a associated Service domain, select ```MQTT```as protocol.
Click ```Generate Certificates``` to generate .X509 certificates for device authentication. Download the certificates before clicking ```Next```. In the next step, add the MQTT Topic your Weather stations publishes it's data on.

!["MQTT topic"](mqtttopic.png)

In this example my ESP32 microcontroller publishes on the MQTT topic ```weather\data```.

Click on ```Next```. Assign the incoming data to the category we created earlier in this step.

!["Category map"](categoryMap.png)

Click on ```Create```.

## Step 3 - Create function

Select the project we created in step 1 from the drop-down at the top of the menu on the left.
Open the ```Functions and Data Pipelines``` section in the menu. Switch to the ```Functions``` tab and click ```Create```. Give your function a name and a description. Select language and runtime environment.
In my example Im using Python and the built in Python3 Env runtime environment.

!["Serverless"](serverless.png)

Click on ```Next```.
The function I am using is simply outputting the incoming data to the service domain log before sending the data forwards in the data pipeline. Upload your function or copy and paste.

```python
import logging
import json


'''
Example payload
{"measurement":"weather",
 "tags": { "Area": "Italy", "Location": "Aprilia" },
 "fields": {"temperature" : "25","humidity" : "52","latitude" : "41.79642","longitude" : "12.42329","altitude" : "76.4"}}
'''
def main(ctx,msg):
    payload = json.loads(msg)
    logging.info("***** Validating *****")
    if(payload['measurement'] == "weather"):
        logging.info("fields are: " + str(payload["fields"]))
    else:
        logging.info("Unknown measurement")

    return ctx.send(str.encode(json.dumps(payload)))#!/usr/bin/python

```

Click on ```Create``` down in the right corner.

## Step 4 - Create a Data pipeline

Next step is to connect our data source to our function using a ```Data pipeline```.
Click on ```Functions and Data Pipelines``` in the menu and select the ```Data Pipelines``` tab.
Click on ``` Create```

Give the Data pipeline a Name
Under ```Input``` select ```Data source``` and then ```IncommingData``` and ```weather``` category from step 2.
Under ```Transformation``` select our function from step 3.
Under ```Output``` select ```Publish to service domain```,
select ```Kafka``` as Endpoint type and enter ```data``` as Endpoint Name.
!["data pipeline"](dataPipeline.png)

Click on ```Create``` down in the right corner.

## Step 5 - Deploy Kubernetes Application

The next and final step is to deploy the kubernetes applications.
Select ```Kubernetes Apps``` from the menu. Click on ```Create```.

Enter a name for our application.
Select your Service Domain.
Click on ```Next``` down in the right corner.

In my example I am deploying 3 containers.

* Kafka consumer
* Influx DB
* Grafana

#### Kafka consumer

This is a simple python application that consumes data from the Kafka service and inputs the data to the influx data base. It is available as an image (voxic/xektia) on dockerhub.

Source:

```python
import os
from kafka import KafkaConsumer
from influxdb import InfluxDBClient
import json

KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC') or print("KAFKA_TOPIC Not defined")
KAFKA_SERVER = os.environ.get('KAFKA_SERVER') or print("KAFKA_SERVER Not defined")
INFLUXDB_SERVER = os.environ.get('INFLUXDB_SERVER') or print("INFLUXDB_SERVER Not defined")
print("KAFKA_TOPIC " + KAFKA_TOPIC)
print("KAFKA_SERVER " + KAFKA_SERVER)
print("INFLUXDB_SERVER " + INFLUXDB_SERVER)

client = InfluxDBClient(host=INFLUXDB_SERVER, port=8086)

if 'WeatherHistory' in str(client.get_list_database()):
    client.switch_database('WeatherHistory')
else:
    client.create_database('WeatherHistory')
    client.switch_database('WeatherHistory')

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_SERVER,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='simple-consumers')

for msg in consumer:
    print (msg)
    data = json.loads(msg.value)
    value = [data]
    client.write_points(value)
    print("Data written to DB : " + str(value))
```

#### Influx DB

Influx DB is an open source time series database. More info at https://www.influxdata.com/

#### Grafana

Grafana is an open source tool for building dashboards. More info at https://grafana.com/

---

To deploy our applications paste the following deployment configuration:

```yaml
---
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: task-influx-claim2
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 3Gi
---
kind: Deployment
apiVersion: apps/v1
metadata:
  name: influxdb
spec:
  replicas: 1
  selector:
    matchLabels:
      app: influxdb
  template:
    metadata:
      labels:
        app: influxdb
    spec:
      volumes:
        - name: var-lib-influxdb
          persistentVolumeClaim:
            claimName: task-influx-claim2
# influxDB 1.7 is necessary to make TrackMap plugin to work in Grafana
      containers:
        - name: influxdb
          image: 'docker.io/influxdb:1.7'
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8086
          volumeMounts:
            - mountPath: /var/lib/influxdb
              name: var-lib-influxdb
---
apiVersion: v1
kind: Service
metadata:
  name: svc-influxdb
  labels:
    app: influxdb
spec:
  type: NodePort
  ports:
    - port: 8086
  selector:
    app: influxdb
---
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: task-grafana-claim
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 3Gi
---
kind: Deployment
apiVersion: apps/v1
metadata:
  name: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      volumes:
        - name: var-lib-grafana
          persistentVolumeClaim:
            claimName: task-grafana-claim  
      containers:
        - name: grafana
          image: grafana/grafana
          imagePullPolicy: IfNotPresent
# environment variable GF_INSTALL_PLUGINS=pr0ps-trackmap-panel introduced to install the TrackMap plugin
# when grafana docker container is created
          env:
            - name: GF_INSTALL_PLUGINS
              value: pr0ps-trackmap-panel
          ports:
            - name: web
              containerPort: 3000
          volumeMounts:
            - mountPath: /var/lib/grafana
              name: var-lib-grafana
---
apiVersion: v1
kind: Service
metadata:
  name: svc-grafana
  annotations:
    sherlock.nutanix.com/http-ingress-path: /
spec:
  ports:
    - protocol: TCP
      name: web
      port: 3000
  selector:
    app: grafana
---
kind: Deployment
apiVersion: apps/v1
metadata:
  name: xi-kafka-influx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: xi-kafka-influx
  template:
    metadata:
      labels:
        app: xi-kafka-influx
    spec:
      containers:
        - name: xi-kafka-influx
          image: ggadax/xektia:xektiav1
          imagePullPolicy: Always
          env:
            - name: KAFKA_SERVER
              value: '{{.Services.Kafka.Endpoint}}'
            - name: KAFKA_TOPIC
              value: weather-data
            - name: INFLUXDB_SERVER
              value: svc-influxdb  
```

Click on ```Next``` down in the right corner. We don't need any outputs so click on ```Create``` down in the right corner.
This deployment creates two persistent volume claims, one for Influx DB and one for Grafana for data persistency. It also makes use of the built in Ingress controller to publish the Grafana user interface.

We have now finished the setup of Xi IoT Weather Station.

## Accessing Grafana

To access the Grafana user interface open your browser and typ in the ip to your service domain (```https://ip-to-servicedomain/```).
Default username _and_ password for Grafana is ```admin```

#### Configuring Grafana data source (connecting Grafana to InfluxDB)

In Grafana click on the cogs icon in the menu on the left. Click on ```Data Sources```.
Click ```Add Data Source```.
Fill in settings:

!["Grafana db"](grafanaDB.png)

Click on ```Save and Test```.

Once the data source is connected you can import this template Dashboard (WeatherStat-1600098838539.json) using the ```+``` in the left menu to import JSON.

Plug the ESP32 to a usb powerbank or into your car , activate the hotspot on your mobile and go !

Here an example just going from Aprilia to Rome. I started the air conditioned and then set it off to make some changes to temperature and humidity.

![Grafana1](grafana1.png)

![Grafana2](grafana2.png)
