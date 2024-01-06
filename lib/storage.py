#!/usr/bin/env python3

import os
import boto3

class Storage(object):
    def __init__(self):
        self.session = boto3.session.Session()
        self.bucket = os.getenv("WASABI_BUCKET") 

        self.s3 = self.session.client('s3',
            aws_access_key_id=os.getenv("WASABI_KEY"), 
            aws_secret_access_key=os.getenv("WASABI_SECRET"),
            endpoint_url=os.getenv("WASABI_ENDPOINT") )

    # Download file from s3 and return bytes buffer
    def get_sampleobj(self, dlpath):
        try:
            return True, self.s3.get_object(
                Bucket=self.bucket, 
                Key=dlpath).get(
                    "Body", "").read()
            return 
        except Exception as e:
            print(e)
        
        return False, b""