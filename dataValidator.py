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
    
    return ctx.send(str.encode(json.dumps(payload)))
