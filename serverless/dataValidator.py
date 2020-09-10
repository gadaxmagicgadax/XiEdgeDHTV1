import logging
import json

'''
Example payload
    {
    'measurement' : 'temperature',
    'value' : '23.3'
    }
'''
def main(ctx,msg):
    payload = json.loads(msg)
    logging.info("***** Validating *****")
    if(payload['measurement'] == "temperature"):
        logging.info("Temperature is: " + payload["value"])
    elif(payload['measurement'] == "rain"):
        logging.info("Rain is: " + payload["value"])
    elif(payload['measurement'] == "wind"):
        logging.info("Wind is: " + payload["value"])
    elif(payload['measurement'] == "latitude"):
        logging.info("Latitude is: " + payload["value"])
    elif(payload['measurement'] == "longitude"):
        logging.info("Longitude is: " + payload["value"])
    elif(payload['measurement'] == "altitude"):
        logging.info("Altitude is: " + payload["value"])
    else:
        logging.info("Unknown measurement")                  
    
    return ctx.send(str.encode(json.dumps(payload)))