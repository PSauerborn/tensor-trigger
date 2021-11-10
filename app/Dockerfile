FROM python:3.8-buster AS build

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

FROM python:3.8-slim

WORKDIR /app

COPY --from=build /root/.cache /root/.cache
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src ./
COPY *.py ./

CMD [ "python", "api.py" ]
