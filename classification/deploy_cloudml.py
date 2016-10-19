#!/usr/bin/env python
# Copyright 2016 Global Fishing Watch. All Rights Reserved.
# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import print_function
import yaml
import json
import time
import subprocess
import os
import datetime
import argparse
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery
import tempfile


def launch(model_name):
    # Read the configuration file so that we 
    # know the train path and don't need to
    # hardcode it here
    with open("deploy_cloudml_config_template.txt") as f:
        config_template = f.read()

    user_name = os.environ['USER']
    time_stamp = datetime.datetime.utcnow().strftime('%y%m%d_%H%M%S')
    job_id = model_name.replace('.', '_') + '_' + time_stamp

    config_txt = config_template.format(
        model_name=model_name, job_id=job_id, user_name=user_name)

    # Kick off the job on CloudML
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(config_txt)
        temp.flush()
        subprocess.check_call([
            'gcloud', 'beta', 'ml', 'jobs', 'submit', 'training', job_id,
            '--config', temp.name, '--module-name',
            'classification.run_training', '--staging-bucket',
            'gs://world-fishing-827-ml', '--package-path', 'classification'
        ])

    return job_id


LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def print_logs(job_id, level="INFO"):
    print('Printing logs of', level, "and above")

    if level not in LEVELS:
        raise ValueError("unknown log level", level)
    level_n = LEVELS.index(level)

    # The API for checking a job's progress.
    # TODO: update this to beta interface.
    # credentials = GoogleCredentials.get_application_default()
    # cloudml = discovery.build('ml', 'v1alpha3', credentials=credentials,
    #                   discoveryServiceUrl='https://storage.googleapis.com/cloud-ml/discovery/ml_v1alpha3_discovery.json')
    # op_name = ('projects/%s/operations/%s' % (project_id, job_id))

    tail = [
        'gcloud', 'beta', 'logging', 'read', '--format=json',
        'labels."ml.googleapis.com/job_id"="%s"' % (job_id, )
    ]
    while True:
        entries = json.loads(subprocess.check_output(tail))

        if not entries:
            time.sleep(10)
            continue

        # The entries aren't guaranteed to be in sorted order
        entries.sort(key=lambda e: e['timestamp'])

        for entry in entries:
            try:
                entry_level_n = LEVELS.index(entry.get("severity"))
            except:
                continue
            if entry_level_n >= level_n:
                if 'jsonPayload' in entry:
                    text = entry['jsonPayload']['message']
                elif 'textPayload' in entry:
                    text = entry['textPayload']
                else:
                    print("Uninterpretable log entry:", entry)
                    continue
                print(text)
                if text.strip() in [
                        "Job failed.", "Job completed successfully."
                ]:
                    return
        last_timestamp = entries[-1]['timestamp']

        tail[-1] = ('labels."ml.googleapis.com/job_id"="%s" AND '
                    'timestamp>"%s"' % (job_id, last_timestamp))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Deploy ML Training.')
    parser.add_argument('model_name', help='module name of model')

    args = parser.parse_args()

    job_id = launch(args.model_name)
    print_logs(job_id)
