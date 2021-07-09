# whpa-cdp-patient-management-service

This project provides the cdp patient management service. 

## Deployment

Docker images manually pushed to cdp artifactory (for now).

Image Names:
* `wh-imaging-cdp-docker-local.artifactory.swg-devops.com/cdp/whpa-cdp-patient-management-service:0.0.1`

This image can be used to test locally and avoid building the project via the py-service-wrapper.

Note: Awaiting updates on Jenkins pipeline that will allow us to build and push docker image via Jenkins, until then it is a manual step.

---

## Development

### Setup

We are using Gradle through a [python gradle plugin](https://github.com/xvik/gradle-use-python-plugin) for the build environment.

A virtual env is created at location `python.envPath` as per `build.gradle`. By default your local python binary is used to create that virtual env, the gradle files mimic what we expect in Jenkins but you can provide `python.pythonBinary` to override local python that will be used.

Note: refer the docs for more configuration options.

```bash
gradle tasks # will list all the available tasks
gradle build # will setup virtualenv and create all tests reports and distribution
```

Note: you will need the `taasArtifactoryUsername` and `taasArtifactoryPassword` variables in `gradle.properties`

Update gradle.properties as needed.
### How to Create the Image for this Project

[See CDP Development setup Python section](https://pages.github.ibm.com/WH-Imaging/DevOps-CDP/docs/Dev_setup/Python.html) for details.

See [LinuxForHealth py-service-wrapper](https://github.com/LinuxForHealth/py-service-wrapper) for background and details.

1. Open a terminal window and navigate to the whpa-cdp-patient-management-service project parent directory.

2. Update the gradle.properties line like the following with your artifactory email and key. Do not include the "<" ">". Don't push this change.
```
whImagingPypiVirtual = https://<your artifactory email>:<your artifactory key>@na.artifactory.swg-devops.com/artifactory/api/pypi/wh-imaging-pypi-virtual/simple
```
See [CDP-minio-python-client README](https://github.ibm.com/WH-Imaging/whpa-cdp-minio-python-client) for details related to whImagingPypiVirtual usage.

3. Run the following command to create the python pip installable "wheel" file:

   ```bash
   gradle clean build -b local.build.gradle # dist is under build/dist by default as per gradle.properties file
   ```

   Note: on Windows the "clean" step will fail in Powershell because it needs the linux `rm` command. Windows "git bash" can be used instead.

4. Create the container using the docker build command below. Add your artifactory id and key where specified:
    ```bash
    docker build --build-arg USERNAME=<your artifactory email> --build-arg PASSWORD=<your artifactory api-key> -t whpa-cdp-patient-management-service:0.0.1 .
    ```

If the steps completed successfully, the image with the name of "IMAGE_NAME" value (whpa-cdp-patient-management-service:0.0.1) should now exist.
Run the image:

```bash
docker run --rm --name whpa-cdp-patient-management-service -p 5000:5000 whpa-cdp-patient-management-service:0.0.1
```
To run the image with MinIO, use the docker-compose file in the test_helper directory. Before doing this, update the docker-compose.yml patient-management-service image name to the one created above. Example:
```
patient-management-service:
  #image: "wh-imaging-cdp-docker-local.artifactory.swg-devops.com/cdp/whpa-cdp-patient-management-service:0.0.1"
  image: "whpa-cdp-patient-management-service:0.0.1" 
```
Run the image with all services from the project directory using the edited docker-compose.yml:
```bash
cd test_helper

docker-compose up -d

OR from the project parent directory:

docker-compose -f test_helper/docker-compose.yml up -d  
```
Browser UI URLs available after docker compose containers start:
- See OpenApi/Swagger section below.
- MinIO: http://localhost:9001/minio

See the project.yaml for the endpoints available. Examples:

```bash
http://localhost:5000/ping  # http GET
```

```bash
http://localhost:5000/patient_bundle  # http POST. See OpenApi for data payload and curl examples.
```

Possible http return codes returned by the patient-management-service:
- 200 Successful.
- 400 Bad request.
- 412 Precondition Failed. The tenant-id may be missing.
- 422 Validation Error. Data payload issue.
- 500 Internal server error. 

#### OpenApi/Swagger URL

http://localhost:5000/docs

An alternative view:
http://localhost:5000/redoc

### Adding Dependency

Update the `build.gradle` and `local.build.gradle` file to add dependencies.

---

### Formatting

We are using [Python Black](https://pypi.org/project/black/) which is a python code formatter. If you are using vscode youcan set it up to use `black` as default formatter for py files

Alternatively you can just run (from within the virtualenv):

```bash
$black <file or directory>
```

---

## Testing

To run unittest, execute:

```bash
gradle clean test
```

For a manual integration test, you can leverage the `docker-compose.yml` file to start MinIO as well as the patient-management-service. MinIO can be used to store example patient bundle data. The MinIO bucket name will be the tenant-id and the bucket's object storage id (OID) will be included in the POST payload (pat_batch_storage_id). See the OpenAPI/SwAGGER URL for the endpoint and the payload structure: http://localhost:5000/docs 

You can edit the `config/minio.ini` and `config/postgres.ini` configuration files based on your environment

To bring up services:

```bash
$docker-compose up -d
```

Note: to make sure you have latest images, execute:

```bash
docker-compose down -v
docker-compose pull
docker-compose up -d
```

#### Example test flow with local MinIO

1. `docker-compose up -d`
2. Put test data in MinIO (http://localhost:9001/minio)
3. Issue the GET http://localhost:5000/patient_bundle (see OpenAPI/Swagger for payload and curl examples)
4. Verify response from GET

---

### VSCODE PYTHON

To setup vscode with the virtualenv and `black` as default python formatter for the project, create a file  `.vscode/settings.json`  , sample below:
```json
#settings.json
{
    "python.formatting.provider": "black",
    "python.pythonPath": "/Users/ayush.garg/.local/share/virtualenvs/whpa-cdp-hl7-batch-receiver-fH1xTusc/bin/python"
}
```

Note: you can set `editor.formatOnSave` to True to automatically formatting files on save

## Changelog

### mm/dd/yyyy -- version 0.0.x
* ...
