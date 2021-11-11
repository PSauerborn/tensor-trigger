FROM python:3.8-buster AS build

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

FROM python:3.8-slim

WORKDIR /app

COPY --from=build /root/.cache /root/.cache
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install -r requirements.txt
RUN apt-get update && apt-get install -y libpq-dev && apt-get clean

COPY src ./src
COPY *.py ./

CMD [ "python", "run_worker.py" ]
