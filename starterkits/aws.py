import boto3
import os   
from google.colab import userdata

try:
  AWS_ACCESS_KEY_ID = userdata.get('AWS_ACCESS_KEY_ID')
  AWS_SECRET_ACCESS_KEY = userdata.get('AWS_SECRET_ACCESS_KEY')
except ImportError:
  AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
  AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')


BUCKET_NAME = 'geospatialsdk'

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)


def download_data_from_s3(bucket_name, prefix, files):
  """Downloads all GIS data for the selected country from the S3 bucket.

  Args:
    bucket_name: The name of the S3 bucket.
    prefix: Prefix/folder path to download.
  """

  # Use paginator to handle large number of objects
  paginator = s3.get_paginator('list_objects_v2')
  pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

  for page in pages:
    for obj in page.get('Contents', []):
      key = obj['Key']
      file = key.split('/')[-1]
      if (file in files) or ('All' in files):
         # Extract the relative path to maintain directory structure
        rel_path = os.path.join('Data', file[0:3], key)
        # rel_path = rel_path.replace('Inputs/', '')
        # Create the local directory if it doesn't exist
        if rel_path:
          os.makedirs(os.path.dirname(rel_path), exist_ok=True)
        # Download the file
        s3.download_file(bucket_name, key, rel_path)
        print(f"Downloaded: {key} to {rel_path}")
      else:
        continue